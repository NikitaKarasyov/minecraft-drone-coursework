import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2

from std_msgs.msg import Bool, Float32, String


class LidarProcessorNode(Node):
    """
    Processes /player/pointcloud as a virtual drone LiDAR.

    Important architecture note:
    minecraft_ros2 publishes point cloud for the Minecraft player.
    In our coursework, player_camera_follow_node keeps the player-camera
    near the visible Allay drone, so /player/pointcloud is treated as the
    drone's LiDAR/depth sensor.

    Subscribes:
    - /player/pointcloud : sensor_msgs/PointCloud2

    Publishes:
    - /drone/lidar_min_distance : std_msgs/Float32
    - /drone/obstacle_near      : std_msgs/Bool
    - /drone/lidar_status       : std_msgs/String

    Coordinate assumptions:
    We assume a ROS-like point cloud frame:
      x = forward
      y = left/right
      z = up/down

    If the Minecraft point cloud uses another convention, change parameters:
      forward_axis, lateral_axis, vertical_axis, forward_sign.
    """

    AXIS_INDEX = {
        'x': 0,
        'y': 1,
        'z': 2,
    }

    def __init__(self):
        super().__init__('lidar_processor_node')

        self.declare_parameter('pointcloud_topic', '/player/pointcloud')
        self.declare_parameter('min_distance_topic', '/drone/lidar_min_distance')
        self.declare_parameter('obstacle_topic', '/drone/obstacle_near')
        self.declare_parameter('status_topic', '/drone/lidar_status')

        # Filtering area in front of the camera/drone.
        self.declare_parameter('forward_axis', 'x')
        self.declare_parameter('lateral_axis', 'y')
        self.declare_parameter('vertical_axis', 'z')
        self.declare_parameter('forward_sign', 1.0)

        self.declare_parameter('min_valid_distance', 0.20)
        self.declare_parameter('max_valid_distance', 20.0)

        # "Corridor" in front of the drone.
        self.declare_parameter('front_lateral_limit', 2.5)
        self.declare_parameter('vertical_min', -1.5)
        self.declare_parameter('vertical_max', 2.5)

        # Safety threshold.
        self.declare_parameter('obstacle_distance_threshold', 3.0)

        # Performance settings.
        self.declare_parameter('process_every_n_messages', 5)
        self.declare_parameter('max_points_to_process', 6000)
        self.declare_parameter('log_period_sec', 1.0)

        self.pointcloud_topic = self.get_parameter('pointcloud_topic').value
        self.min_distance_topic = self.get_parameter('min_distance_topic').value
        self.obstacle_topic = self.get_parameter('obstacle_topic').value
        self.status_topic = self.get_parameter('status_topic').value

        self.forward_axis = self.get_parameter('forward_axis').value
        self.lateral_axis = self.get_parameter('lateral_axis').value
        self.vertical_axis = self.get_parameter('vertical_axis').value
        self.forward_sign = float(self.get_parameter('forward_sign').value)

        self.min_valid_distance = float(self.get_parameter('min_valid_distance').value)
        self.max_valid_distance = float(self.get_parameter('max_valid_distance').value)

        self.front_lateral_limit = float(self.get_parameter('front_lateral_limit').value)
        self.vertical_min = float(self.get_parameter('vertical_min').value)
        self.vertical_max = float(self.get_parameter('vertical_max').value)

        self.obstacle_distance_threshold = float(
            self.get_parameter('obstacle_distance_threshold').value
        )

        self.process_every_n_messages = int(
            self.get_parameter('process_every_n_messages').value
        )
        self.max_points_to_process = int(
            self.get_parameter('max_points_to_process').value
        )
        self.log_period_sec = float(self.get_parameter('log_period_sec').value)

        self.validate_axes()

        self.forward_index = self.AXIS_INDEX[self.forward_axis]
        self.lateral_index = self.AXIS_INDEX[self.lateral_axis]
        self.vertical_index = self.AXIS_INDEX[self.vertical_axis]

        self.msg_count = 0
        self.last_log_time = 0.0

        self.create_subscription(
            PointCloud2,
            self.pointcloud_topic,
            self.pointcloud_callback,
            qos_profile_sensor_data,
        )

        self.min_distance_pub = self.create_publisher(
            Float32,
            self.min_distance_topic,
            10,
        )

        self.obstacle_pub = self.create_publisher(
            Bool,
            self.obstacle_topic,
            10,
        )

        self.status_pub = self.create_publisher(
            String,
            self.status_topic,
            10,
        )

        self.get_logger().info('LiDAR processor started')
        self.get_logger().info(f'PointCloud topic: {self.pointcloud_topic}')
        self.get_logger().info(
            f'Frame convention: forward={self.forward_sign:+.1f}*{self.forward_axis}, '
            f'lateral={self.lateral_axis}, vertical={self.vertical_axis}'
        )
        self.get_logger().info(
            f'Front corridor: lateral <= {self.front_lateral_limit:.2f}, '
            f'vertical in [{self.vertical_min:.2f}, {self.vertical_max:.2f}], '
            f'obstacle threshold={self.obstacle_distance_threshold:.2f}'
        )

    def validate_axes(self):
        axes = [self.forward_axis, self.lateral_axis, self.vertical_axis]

        for axis in axes:
            if axis not in self.AXIS_INDEX:
                raise ValueError(
                    f'Invalid axis "{axis}". Expected one of x, y, z.'
                )

        if len(set(axes)) != 3:
            raise ValueError(
                'forward_axis, lateral_axis and vertical_axis must be different.'
            )

    def pointcloud_callback(self, msg: PointCloud2):
        self.msg_count += 1

        if self.process_every_n_messages > 1:
            if self.msg_count % self.process_every_n_messages != 0:
                return

        result = self.compute_front_min_distance(msg)

        min_distance = result['min_distance']
        front_points = result['front_points']
        processed_points = result['processed_points']
        total_seen_points = result['total_seen_points']

        obstacle_near = (
            math.isfinite(min_distance)
            and min_distance < self.obstacle_distance_threshold
        )

        min_msg = Float32()
        min_msg.data = float(min_distance) if math.isfinite(min_distance) else -1.0
        self.min_distance_pub.publish(min_msg)

        obstacle_msg = Bool()
        obstacle_msg.data = bool(obstacle_near)
        self.obstacle_pub.publish(obstacle_msg)

        if math.isfinite(min_distance):
            status_text = (
                f'min_front_distance={min_distance:.2f}, '
                f'obstacle_near={obstacle_near}, '
                f'front_points={front_points}, '
                f'processed_points={processed_points}, '
                f'total_seen_points={total_seen_points}'
            )
        else:
            status_text = (
                f'no valid front points, '
                f'obstacle_near=False, '
                f'front_points={front_points}, '
                f'processed_points={processed_points}, '
                f'total_seen_points={total_seen_points}'
            )

        status_msg = String()
        status_msg.data = status_text
        self.status_pub.publish(status_msg)

        now = time.monotonic()
        if now - self.last_log_time >= self.log_period_sec:
            self.get_logger().info(status_text)
            self.last_log_time = now

    def compute_front_min_distance(self, msg: PointCloud2):
        min_distance = float('inf')
        front_points = 0
        processed_points = 0
        total_seen_points = 0

        # read_points returns an iterator of x, y, z tuples.
        points = point_cloud2.read_points(
            msg,
            field_names=('x', 'y', 'z'),
            skip_nans=True,
        )

        for point in points:
            total_seen_points += 1

            if processed_points >= self.max_points_to_process:
                break

            x = float(point[0])
            y = float(point[1])
            z = float(point[2])

            coords = (x, y, z)

            forward = self.forward_sign * coords[self.forward_index]
            lateral = coords[self.lateral_index]
            vertical = coords[self.vertical_index]

            # Only points in front of the sensor.
            if forward < self.min_valid_distance:
                continue

            if forward > self.max_valid_distance:
                continue

            # Keep a corridor in front of the drone.
            if abs(lateral) > self.front_lateral_limit:
                continue

            if vertical < self.vertical_min or vertical > self.vertical_max:
                continue

            # Euclidean distance from the sensor.
            distance = math.sqrt(x * x + y * y + z * z)

            if distance < self.min_valid_distance:
                continue

            if distance > self.max_valid_distance:
                continue

            processed_points += 1
            front_points += 1

            if distance < min_distance:
                min_distance = distance

        return {
            'min_distance': min_distance,
            'front_points': front_points,
            'processed_points': processed_points,
            'total_seen_points': total_seen_points,
        }


def main(args=None):
    rclpy.init(args=args)
    node = LidarProcessorNode()

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
