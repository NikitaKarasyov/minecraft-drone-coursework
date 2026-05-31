import math
import time

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
from std_msgs.msg import String
from minecraft_msgs.srv import Command


def distance_3d(a, b) -> float:
    return math.sqrt(
        (a[0] - b[0]) ** 2 +
        (a[1] - b[1]) ** 2 +
        (a[2] - b[2]) ** 2
    )


def move_towards(current, target, max_step):
    dist = distance_3d(current, target)

    if dist <= max_step or dist < 1e-6:
        return target

    ratio = max_step / dist

    return (
        current[0] + (target[0] - current[0]) * ratio,
        current[1] + (target[1] - current[1]) * ratio,
        current[2] + (target[2] - current[2]) * ratio,
    )


class DroneEntityControllerNode(Node):
    """
    Low-level controller for a separate Minecraft entity-drone.

    The drone is an entity with tag "ros_drone", created by drone_spawn_node.

    This node no longer owns the mission route.
    It only receives target points from /drone/target and moves the entity smoothly.

    Subscribes:
    - /drone/target : geometry_msgs/PoseStamped

    Publishes:
    - /drone/pose              : geometry_msgs/PoseStamped
    - /drone/path              : nav_msgs/Path
    - /drone/controller_status : std_msgs/String

    Uses:
    - /minecraft/command service
    """

    def __init__(self):
        super().__init__('drone_entity_controller_node')

        self.declare_parameter('service_name', '/minecraft/command')
        self.declare_parameter('drone_tag', 'ros_drone')

        self.declare_parameter('target_topic', '/drone/target')
        self.declare_parameter('pose_topic', '/drone/pose')
        self.declare_parameter('path_topic', '/drone/path')
        self.declare_parameter('status_topic', '/drone/controller_status')

        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('update_rate', 8.0)
        self.declare_parameter('speed_blocks_per_sec', 2.0)
        self.declare_parameter('target_tolerance', 0.25)

        self.declare_parameter('start_x', 0.0)
        self.declare_parameter('start_y', 8.0)
        self.declare_parameter('start_z', 0.0)

        self.service_name = self.get_parameter('service_name').value
        self.drone_tag = self.get_parameter('drone_tag').value

        self.target_topic = self.get_parameter('target_topic').value
        self.pose_topic = self.get_parameter('pose_topic').value
        self.path_topic = self.get_parameter('path_topic').value
        self.status_topic = self.get_parameter('status_topic').value

        self.frame_id = self.get_parameter('frame_id').value
        self.update_rate = float(self.get_parameter('update_rate').value)
        self.speed = float(self.get_parameter('speed_blocks_per_sec').value)
        self.target_tolerance = float(self.get_parameter('target_tolerance').value)

        start_x = float(self.get_parameter('start_x').value)
        start_y = float(self.get_parameter('start_y').value)
        start_z = float(self.get_parameter('start_z').value)

        # Internal position uses Minecraft coordinates: X, Y, Z.
        self.current_position = (start_x, start_y, start_z)
        self.current_target = None

        self.command_client = self.create_client(Command, self.service_name)

        self.create_subscription(
            PoseStamped,
            self.target_topic,
            self.target_callback,
            10,
        )

        self.pose_pub = self.create_publisher(PoseStamped, self.pose_topic, 10)
        self.path_pub = self.create_publisher(Path, self.path_topic, 10)
        self.status_pub = self.create_publisher(String, self.status_topic, 10)

        self.path_msg = Path()
        self.path_msg.header.frame_id = self.frame_id

        self.timer_period = 1.0 / self.update_rate
        self.timer = self.create_timer(self.timer_period, self.timer_callback)

        self.last_command_time = 0.0
        self.command_in_flight = False

        self.get_logger().info('Drone entity target controller started')
        self.get_logger().info(f'Drone tag: {self.drone_tag}')
        self.get_logger().info(f'Target topic: {self.target_topic}')
        self.get_logger().info(f'Speed: {self.speed:.2f} blocks/sec')

    def target_callback(self, msg: PoseStamped):
        self.current_target = self.ros_pose_to_minecraft_position(msg)
        self.get_logger().info(
            f'New target received: '
            f'({self.current_target[0]:.2f}, {self.current_target[1]:.2f}, {self.current_target[2]:.2f})'
        )

    def ros_pose_to_minecraft_position(self, msg: PoseStamped):
        """
        ROS pose convention in this project:
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
        return (mc_x, mc_y, mc_z)

    def minecraft_position_to_ros_pose(self, mc_position):
        mc_x, mc_y, mc_z = mc_position

        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id

        msg.pose.position.x = mc_x
        msg.pose.position.y = mc_z
        msg.pose.position.z = mc_y
        msg.pose.orientation.w = 1.0

        return msg

    def timer_callback(self):
        if not self.command_client.service_is_ready():
            if not self.command_client.wait_for_service(timeout_sec=0.1):
                self.publish_status('WAITING_FOR_MINECRAFT_COMMAND_SERVICE')
                self.publish_pose_and_path()
                return

        if self.current_target is None:
            self.publish_status('WAITING_FOR_TARGET')
            self.publish_pose_and_path()
            return

        dist = distance_3d(self.current_position, self.current_target)

        if dist <= self.target_tolerance:
            self.publish_status(
                f'HOLDING_TARGET: pos=({self.current_position[0]:.2f}, '
                f'{self.current_position[1]:.2f}, {self.current_position[2]:.2f}), '
                f'distance={dist:.2f}'
            )
            self.publish_pose_and_path()
            self.teleport_drone(self.current_position)
            return

        max_step = self.speed * self.timer_period
        self.current_position = move_towards(
            self.current_position,
            self.current_target,
            max_step,
        )

        self.teleport_drone(self.current_position)
        self.publish_pose_and_path()

        new_dist = distance_3d(self.current_position, self.current_target)
        self.publish_status(
            f'MOVING_TO_TARGET: pos=({self.current_position[0]:.2f}, '
            f'{self.current_position[1]:.2f}, {self.current_position[2]:.2f}), '
            f'target=({self.current_target[0]:.2f}, {self.current_target[1]:.2f}, '
            f'{self.current_target[2]:.2f}), distance={new_dist:.2f}'
        )

    def teleport_drone(self, position):
        if self.command_in_flight:
            return

        x, y, z = position

        command = (
            f'tp @e[tag={self.drone_tag},limit=1,sort=nearest] '
            f'{x:.3f} {y:.3f} {z:.3f}'
        )

        request = Command.Request()
        request.command = command

        future = self.command_client.call_async(request)
        self.command_in_flight = True
        future.add_done_callback(self.command_done_callback)

    def command_done_callback(self, future):
        self.command_in_flight = False

        try:
            response = future.result()
            if response is not None and not response.success:
                self.get_logger().warn(f'Minecraft command failed: {response.message}')
        except Exception as exc:
            self.get_logger().warn(f'Minecraft command exception: {exc}')

    def publish_pose_and_path(self):
        pose_msg = self.minecraft_position_to_ros_pose(self.current_position)
        self.pose_pub.publish(pose_msg)

        self.path_msg.header.stamp = pose_msg.header.stamp
        self.path_msg.poses.append(pose_msg)

        if len(self.path_msg.poses) > 2000:
            self.path_msg.poses = self.path_msg.poses[-2000:]

        self.path_pub.publish(self.path_msg)

    def publish_status(self, text: str):
        msg = String()
        msg.data = text
        self.status_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = DroneEntityControllerNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Interrupted by user')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
