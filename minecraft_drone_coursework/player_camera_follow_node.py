import math
import time

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from minecraft_msgs.srv import Command


class PlayerCameraFollowNode(Node):
    """
    Keeps the Minecraft player-camera near the visible drone entity.

    Why this node is needed:
    - minecraft_ros2 publishes sensors for the player:
        /player/pointcloud
        /player/image_raw
        /player/imu
    - our visible drone is a separate entity, for example Allay with tag ros_drone;
    - therefore, we use the player as a virtual sensor rig synchronized with the drone.

    The node subscribes to:
    - /drone/pose

    And controls the Minecraft player via:
    - /minecraft/command

    It teleports the player with a fixed offset from the drone and points the camera
    toward the drone.
    """

    def __init__(self):
        super().__init__('player_camera_follow_node')

        self.declare_parameter('service_name', '/minecraft/command')
        self.declare_parameter('drone_pose_topic', '/drone/pose')
        self.declare_parameter('camera_status_topic', '/drone/camera_status')

        self.declare_parameter('player_selector', '@p')

        # Camera offset in Minecraft coordinates:
        # X horizontal, Y vertical, Z horizontal.
        self.declare_parameter('offset_x', -5.0)
        self.declare_parameter('offset_y', 3.0)
        self.declare_parameter('offset_z', -5.0)

        self.declare_parameter('follow_rate', 4.0)
        self.declare_parameter('look_at_drone', True)

        self.declare_parameter('fixed_yaw', 45.0)
        self.declare_parameter('fixed_pitch', 25.0)

        self.declare_parameter('set_spectator_mode', True)
        self.declare_parameter('restore_creative_on_exit', True)

        self.service_name = self.get_parameter('service_name').value
        self.drone_pose_topic = self.get_parameter('drone_pose_topic').value
        self.camera_status_topic = self.get_parameter('camera_status_topic').value

        self.player_selector = self.get_parameter('player_selector').value

        self.offset_x = float(self.get_parameter('offset_x').value)
        self.offset_y = float(self.get_parameter('offset_y').value)
        self.offset_z = float(self.get_parameter('offset_z').value)

        self.follow_rate = float(self.get_parameter('follow_rate').value)
        self.look_at_drone = bool(self.get_parameter('look_at_drone').value)

        self.fixed_yaw = float(self.get_parameter('fixed_yaw').value)
        self.fixed_pitch = float(self.get_parameter('fixed_pitch').value)

        self.set_spectator_mode = bool(self.get_parameter('set_spectator_mode').value)
        self.restore_creative_on_exit = bool(
            self.get_parameter('restore_creative_on_exit').value
        )

        self.command_client = self.create_client(Command, self.service_name)

        self.create_subscription(
            PoseStamped,
            self.drone_pose_topic,
            self.drone_pose_callback,
            10,
        )

        self.status_pub = self.create_publisher(String, self.camera_status_topic, 10)

        self.last_drone_pose = None
        self.service_ready = False
        self.spectator_configured = False
        self.pending_command = False
        self.last_wait_log_time = 0.0

        timer_period = 1.0 / self.follow_rate
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.get_logger().info('Player camera follow node started')
        self.get_logger().info(f'Drone pose topic: {self.drone_pose_topic}')
        self.get_logger().info(f'Minecraft command service: {self.service_name}')
        self.get_logger().info(
            f'Camera offset: x={self.offset_x}, y={self.offset_y}, z={self.offset_z}'
        )

    def drone_pose_callback(self, msg: PoseStamped):
        self.last_drone_pose = msg

    def ros_pose_to_minecraft_position(self, msg: PoseStamped):
        """
        Convert /drone/pose to Minecraft coordinates.

        drone_entity_controller_node publishes:
          ROS x = Minecraft X
          ROS y = Minecraft Z
          ROS z = Minecraft Y

        Therefore:
          Minecraft X = ROS x
          Minecraft Y = ROS z
          Minecraft Z = ROS y
        """
        mc_x = msg.pose.position.x
        mc_y = msg.pose.position.z
        mc_z = msg.pose.position.y
        return mc_x, mc_y, mc_z

    def compute_yaw_pitch_to_look_at(self, camera_pos, target_pos):
        cam_x, cam_y, cam_z = camera_pos
        target_x, target_y, target_z = target_pos

        dx = target_x - cam_x
        dy = target_y - cam_y
        dz = target_z - cam_z

        horizontal = math.sqrt(dx * dx + dz * dz)

        # Minecraft yaw:
        # 0 looks along +Z, 90 looks roughly to -X, -90 to +X.
        yaw = math.degrees(math.atan2(-dx, dz))

        # Minecraft pitch:
        # positive values look down, negative values look up.
        pitch = math.degrees(math.atan2(-dy, max(horizontal, 1e-6)))

        return yaw, pitch

    def call_command_async(self, command: str):
        request = Command.Request()
        request.command = command

        future = self.command_client.call_async(request)
        self.pending_command = True
        future.add_done_callback(self.command_done_callback)

    def command_done_callback(self, future):
        self.pending_command = False

        try:
            response = future.result()
            if response is not None and not response.success:
                self.get_logger().warn(f'Minecraft command failed: {response.message}')
        except Exception as exc:
            self.get_logger().warn(f'Minecraft command exception: {exc}')

    def publish_status(self, text: str):
        msg = String()
        msg.data = text
        self.status_pub.publish(msg)

    def timer_callback(self):
        if not self.service_ready:
            self.service_ready = self.command_client.wait_for_service(timeout_sec=0.1)

            if not self.service_ready:
                now = time.monotonic()
                if now - self.last_wait_log_time > 2.0:
                    self.get_logger().info('Waiting for /minecraft/command service...')
                    self.last_wait_log_time = now

                self.publish_status('WAITING_FOR_MINECRAFT_COMMAND_SERVICE')
                return

        if self.set_spectator_mode and not self.spectator_configured:
            self.call_command_async(f'gamemode spectator {self.player_selector}')
            self.spectator_configured = True
            self.publish_status('SPECTATOR_MODE_ENABLED')
            return

        if self.last_drone_pose is None:
            now = time.monotonic()
            if now - self.last_wait_log_time > 2.0:
                self.get_logger().info(f'Waiting for {self.drone_pose_topic}...')
                self.last_wait_log_time = now

            self.publish_status('WAITING_FOR_DRONE_POSE')
            return

        if self.pending_command:
            return

        drone_x, drone_y, drone_z = self.ros_pose_to_minecraft_position(
            self.last_drone_pose
        )

        camera_x = drone_x + self.offset_x
        camera_y = drone_y + self.offset_y
        camera_z = drone_z + self.offset_z

        if self.look_at_drone:
            yaw, pitch = self.compute_yaw_pitch_to_look_at(
                (camera_x, camera_y, camera_z),
                (drone_x, drone_y, drone_z),
            )
        else:
            yaw = self.fixed_yaw
            pitch = self.fixed_pitch

        command = (
            f'tp {self.player_selector} '
            f'{camera_x:.3f} {camera_y:.3f} {camera_z:.3f} '
            f'{yaw:.2f} {pitch:.2f}'
        )

        self.call_command_async(command)

        self.publish_status(
            f'FOLLOWING_DRONE: '
            f'camera=({camera_x:.2f}, {camera_y:.2f}, {camera_z:.2f}), '
            f'drone=({drone_x:.2f}, {drone_y:.2f}, {drone_z:.2f}), '
            f'yaw={yaw:.1f}, pitch={pitch:.1f}'
        )

    def restore_player_mode(self):
        if not self.restore_creative_on_exit:
            return

        if not self.command_client.service_is_ready():
            return

        request = Command.Request()
        request.command = f'gamemode creative {self.player_selector}'

        future = self.command_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=1.0)


def main(args=None):
    rclpy.init(args=args)
    node = PlayerCameraFollowNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Interrupted by user')
    finally:
        node.restore_player_mode()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
