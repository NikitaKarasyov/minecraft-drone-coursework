import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Pose
from sensor_msgs.msg import Imu
from std_msgs.msg import String


class SensorMonitorNode(Node):
    """
    Monitors Minecraft player-agent sensors.

    Subscribes:
    - /player/ground_truth : geometry_msgs/Pose
    - /player/imu          : sensor_msgs/Imu

    Publishes:
    - /drone/status        : std_msgs/String
    """

    def __init__(self):
        super().__init__('sensor_monitor_node')

        self.declare_parameter('pose_topic', '/player/ground_truth')
        self.declare_parameter('imu_topic', '/player/imu')
        self.declare_parameter('status_topic', '/drone/status')
        self.declare_parameter('report_period_sec', 1.0)

        self.pose_topic = self.get_parameter('pose_topic').value
        self.imu_topic = self.get_parameter('imu_topic').value
        self.status_topic = self.get_parameter('status_topic').value
        self.report_period_sec = float(self.get_parameter('report_period_sec').value)

        self.last_pose = None
        self.imu_count = 0

        self.create_subscription(Pose, self.pose_topic, self.pose_callback, 10)
        self.create_subscription(Imu, self.imu_topic, self.imu_callback, 10)

        self.status_pub = self.create_publisher(String, self.status_topic, 10)
        self.timer = self.create_timer(self.report_period_sec, self.timer_callback)

        self.get_logger().info('Sensor monitor started')
        self.get_logger().info(f'Pose topic: {self.pose_topic}')
        self.get_logger().info(f'IMU topic: {self.imu_topic}')
        self.get_logger().info(f'Status topic: {self.status_topic}')

    def pose_callback(self, msg: Pose):
        self.last_pose = msg

    def imu_callback(self, msg: Imu):
        self.imu_count += 1

    def timer_callback(self):
        status_msg = String()

        if self.last_pose is None:
            status_msg.data = f'Waiting for pose on {self.pose_topic}...'
        else:
            p = self.last_pose.position
            q = self.last_pose.orientation

            status_msg.data = (
                f'pose=({p.x:.2f}, {p.y:.2f}, {p.z:.2f}), '
                f'orientation=({q.x:.2f}, {q.y:.2f}, {q.z:.2f}, {q.w:.2f}), '
                f'imu_messages={self.imu_count}'
            )

        self.get_logger().info(status_msg.data)
        self.status_pub.publish(status_msg)


def main(args=None):
    rclpy.init(args=args)
    node = SensorMonitorNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
