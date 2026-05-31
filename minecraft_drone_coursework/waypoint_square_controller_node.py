import math
import time

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Pose, Twist


def normalize_angle(angle: float) -> float:
    """Normalize angle to [-pi, pi]."""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


def yaw_from_quaternion_z_w(z: float, w: float) -> float:
    """
    Extract planar yaw from quaternion.

    For this Minecraft ROS setup we mainly observe z/w orientation components.
    """
    return 2.0 * math.atan2(z, w)


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


class WaypointSquareControllerNode(Node):
    """
    Coordinate-based square patrol controller.

    The node:
    - subscribes to /player/ground_truth;
    - takes the first received pose as the square origin;
    - builds a square route that matches the colored markers from world_setup_node;
    - publishes Twist commands to /cmd_vel;
    - robustly stops after mission completion or Ctrl+C.

    This is better than a time-based patrol because the controller uses
    the real player position from Minecraft.
    """

    def __init__(self):
        super().__init__('waypoint_square_controller_node')

        self.declare_parameter('pose_topic', '/player/ground_truth')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')

        self.declare_parameter('side_length', 8.0)
        self.declare_parameter('loops', 1)

        self.declare_parameter('linear_speed', 0.45)
        self.declare_parameter('max_angular_speed', 0.75)

        self.declare_parameter('position_tolerance', 0.55)
        self.declare_parameter('yaw_tolerance', 0.25)

        self.declare_parameter('k_linear', 0.45)
        self.declare_parameter('k_angular', 1.40)

        self.declare_parameter('publish_rate', 20.0)
        self.declare_parameter('start_delay_sec', 2.0)

        # If the route goes in the mirrored direction, change y_axis_sign to -1.0.
        self.declare_parameter('x_axis_sign', 1.0)
        self.declare_parameter('y_axis_sign', 1.0)

        # If turns go in the wrong direction, change angular_sign to -1.0.
        self.declare_parameter('angular_sign', 1.0)

        self.pose_topic = self.get_parameter('pose_topic').value
        self.cmd_vel_topic = self.get_parameter('cmd_vel_topic').value

        self.side_length = float(self.get_parameter('side_length').value)
        self.loops = int(self.get_parameter('loops').value)

        self.linear_speed = float(self.get_parameter('linear_speed').value)
        self.max_angular_speed = float(self.get_parameter('max_angular_speed').value)

        self.position_tolerance = float(self.get_parameter('position_tolerance').value)
        self.yaw_tolerance = float(self.get_parameter('yaw_tolerance').value)

        self.k_linear = float(self.get_parameter('k_linear').value)
        self.k_angular = float(self.get_parameter('k_angular').value)

        self.publish_rate = float(self.get_parameter('publish_rate').value)
        self.start_delay_sec = float(self.get_parameter('start_delay_sec').value)

        self.x_axis_sign = float(self.get_parameter('x_axis_sign').value)
        self.y_axis_sign = float(self.get_parameter('y_axis_sign').value)
        self.angular_sign = float(self.get_parameter('angular_sign').value)

        self.cmd_pub = self.create_publisher(Twist, self.cmd_vel_topic, 10)
        self.pose_sub = self.create_subscription(
            Pose,
            self.pose_topic,
            self.pose_callback,
            10,
        )

        self.last_pose = None
        self.origin = None
        self.waypoints = []
        self.current_waypoint_index = 0

        self.node_start_time = time.monotonic()
        self.mission_started = False
        self.mission_finished = False

        timer_period = 1.0 / self.publish_rate
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.get_logger().info('Waypoint square controller started')
        self.get_logger().info(f'Pose topic: {self.pose_topic}')
        self.get_logger().info(f'Cmd topic: {self.cmd_vel_topic}')
        self.get_logger().info(
            f'side_length={self.side_length}, loops={self.loops}, '
            f'linear_speed={self.linear_speed}, max_angular_speed={self.max_angular_speed}'
        )

    def pose_callback(self, msg: Pose):
        self.last_pose = msg

        if self.origin is None:
            self.origin = (msg.position.x, msg.position.y)
            self.build_waypoints()
            self.get_logger().info(
                f'Origin locked: x={self.origin[0]:.2f}, y={self.origin[1]:.2f}'
            )
            self.log_waypoints()

    def build_waypoints(self):
        ox, oy = self.origin
        dx = self.side_length * self.x_axis_sign
        dy = self.side_length * self.y_axis_sign

        one_loop = [
            (ox, oy),           # gold/start
            (ox + dx, oy),      # redstone
            (ox + dx, oy + dy), # emerald
            (ox, oy + dy),      # lapis
            (ox, oy),           # back to start
        ]

        self.waypoints = []
        for _ in range(self.loops):
            # For the first loop, include the start point only once.
            if not self.waypoints:
                self.waypoints.extend(one_loop)
            else:
                self.waypoints.extend(one_loop[1:])

    def log_waypoints(self):
        for i, (x, y) in enumerate(self.waypoints):
            self.get_logger().info(f'Waypoint {i}: x={x:.2f}, y={y:.2f}')

    def timer_callback(self):
        if self.mission_finished:
            self.publish_stop()
            return

        if self.last_pose is None:
            self.publish_stop()
            self.get_logger().info('Waiting for /player/ground_truth...')
            return

        if self.origin is None or not self.waypoints:
            self.publish_stop()
            return

        if not self.mission_started:
            elapsed = time.monotonic() - self.node_start_time
            self.publish_stop()

            if elapsed >= self.start_delay_sec:
                self.mission_started = True
                self.get_logger().info('Mission started')
            return

        if self.current_waypoint_index >= len(self.waypoints):
            self.finish_mission()
            return

        self.navigate_to_current_waypoint()

    def navigate_to_current_waypoint(self):
        pose = self.last_pose

        current_x = pose.position.x
        current_y = pose.position.y

        target_x, target_y = self.waypoints[self.current_waypoint_index]

        error_x = target_x - current_x
        error_y = target_y - current_y
        distance = math.hypot(error_x, error_y)

        if distance <= self.position_tolerance:
            self.get_logger().info(
                f'Waypoint {self.current_waypoint_index} reached: '
                f'target=({target_x:.2f}, {target_y:.2f}), '
                f'current=({current_x:.2f}, {current_y:.2f}), '
                f'distance={distance:.2f}'
            )
            self.current_waypoint_index += 1
            self.publish_stop()

            if self.current_waypoint_index >= len(self.waypoints):
                self.finish_mission()
            else:
                next_x, next_y = self.waypoints[self.current_waypoint_index]
                self.get_logger().info(
                    f'Next waypoint {self.current_waypoint_index}: '
                    f'x={next_x:.2f}, y={next_y:.2f}'
                )
            return

        target_yaw = math.atan2(error_y, error_x)
        current_yaw = yaw_from_quaternion_z_w(
            pose.orientation.z,
            pose.orientation.w,
        )

        yaw_error = normalize_angle(target_yaw - current_yaw)

        msg = Twist()

        if abs(yaw_error) > self.yaw_tolerance:
            # Rotate in place first.
            msg.linear.x = 0.0
            msg.angular.z = self.angular_sign * clamp(
                self.k_angular * yaw_error,
                -self.max_angular_speed,
                self.max_angular_speed,
            )
        else:
            # Move forward with small heading correction.
            msg.linear.x = clamp(
                self.k_linear * distance,
                0.12,
                self.linear_speed,
            )
            msg.angular.z = self.angular_sign * clamp(
                self.k_angular * yaw_error,
                -self.max_angular_speed,
                self.max_angular_speed,
            )

        self.cmd_pub.publish(msg)

    def publish_stop(self):
        self.cmd_pub.publish(Twist())

    def publish_stop_burst(self, duration_sec: float = 1.0, rate_hz: float = 20.0):
        self.get_logger().info('Publishing stop burst...')
        end_time = time.monotonic() + duration_sec
        sleep_time = 1.0 / rate_hz

        while time.monotonic() < end_time:
            self.publish_stop()
            rclpy.spin_once(self, timeout_sec=0.0)
            time.sleep(sleep_time)

        self.get_logger().info('Stop burst completed')

    def finish_mission(self):
        self.get_logger().info('Square waypoint mission completed')
        self.publish_stop_burst()
        self.mission_finished = True


def main(args=None):
    rclpy.init(args=args)
    node = WaypointSquareControllerNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Interrupted by user')
    finally:
        node.publish_stop_burst()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
