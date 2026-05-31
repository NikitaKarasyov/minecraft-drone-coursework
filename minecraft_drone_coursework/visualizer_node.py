import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray


class VisualizerNode(Node):
    """
    Publishes visualization markers for RViz2.

    Subscribes:
    - /drone/pose
    - /drone/target
    - /drone/goal

    Publishes:
    - /drone/markers

    The node visualizes:
    - current drone position;
    - current controller target;
    - current mission goal;
    - waypoint pads;
    - inspection target;
    - known obstacles/no-fly zones.
    """

    def __init__(self):
        super().__init__('visualizer_node')

        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('marker_topic', '/drone/markers')
        self.declare_parameter('status_topic', '/drone/visualizer_status')

        self.declare_parameter('drone_pose_topic', '/drone/pose')
        self.declare_parameter('target_topic', '/drone/target')
        self.declare_parameter('goal_topic', '/drone/goal')

        self.declare_parameter('publish_rate', 2.0)

        self.frame_id = self.get_parameter('frame_id').value
        self.marker_topic = self.get_parameter('marker_topic').value
        self.status_topic = self.get_parameter('status_topic').value

        self.drone_pose_topic = self.get_parameter('drone_pose_topic').value
        self.target_topic = self.get_parameter('target_topic').value
        self.goal_topic = self.get_parameter('goal_topic').value

        self.publish_rate = float(self.get_parameter('publish_rate').value)

        self.last_drone_pose = None
        self.last_target = None
        self.last_goal = None

        self.create_subscription(
            PoseStamped,
            self.drone_pose_topic,
            self.drone_pose_callback,
            10,
        )

        self.create_subscription(
            PoseStamped,
            self.target_topic,
            self.target_callback,
            10,
        )

        self.create_subscription(
            PoseStamped,
            self.goal_topic,
            self.goal_callback,
            10,
        )

        self.marker_pub = self.create_publisher(MarkerArray, self.marker_topic, 10)
        self.status_pub = self.create_publisher(String, self.status_topic, 10)

        self.timer = self.create_timer(1.0 / self.publish_rate, self.timer_callback)

        self.get_logger().info('Visualizer node started')
        self.get_logger().info(f'Publishing markers to {self.marker_topic}')

    def drone_pose_callback(self, msg):
        self.last_drone_pose = msg

    def target_callback(self, msg):
        self.last_target = msg

    def goal_callback(self, msg):
        self.last_goal = msg

    def base_marker(self, marker_id, ns, marker_type):
        marker = Marker()
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.header.frame_id = self.frame_id
        marker.ns = ns
        marker.id = marker_id
        marker.type = marker_type
        marker.action = Marker.ADD
        marker.pose.orientation.w = 1.0
        marker.lifetime.sec = 0
        marker.lifetime.nanosec = 0
        return marker

    def set_color(self, marker, r, g, b, a):
        marker.color.r = float(r)
        marker.color.g = float(g)
        marker.color.b = float(b)
        marker.color.a = float(a)

    def make_sphere(self, marker_id, ns, x, y, z, scale, color):
        marker = self.base_marker(marker_id, ns, Marker.SPHERE)
        marker.pose.position.x = float(x)
        marker.pose.position.y = float(y)
        marker.pose.position.z = float(z)
        marker.scale.x = float(scale)
        marker.scale.y = float(scale)
        marker.scale.z = float(scale)
        self.set_color(marker, *color)
        return marker

    def make_cube(self, marker_id, ns, x, y, z, sx, sy, sz, color):
        marker = self.base_marker(marker_id, ns, Marker.CUBE)
        marker.pose.position.x = float(x)
        marker.pose.position.y = float(y)
        marker.pose.position.z = float(z)
        marker.scale.x = float(sx)
        marker.scale.y = float(sy)
        marker.scale.z = float(sz)
        self.set_color(marker, *color)
        return marker

    def make_cylinder(self, marker_id, ns, x, y, z, sx, sy, sz, color):
        marker = self.base_marker(marker_id, ns, Marker.CYLINDER)
        marker.pose.position.x = float(x)
        marker.pose.position.y = float(y)
        marker.pose.position.z = float(z)
        marker.scale.x = float(sx)
        marker.scale.y = float(sy)
        marker.scale.z = float(sz)
        self.set_color(marker, *color)
        return marker

    def make_text(self, marker_id, ns, x, y, z, text, scale, color):
        marker = self.base_marker(marker_id, ns, Marker.TEXT_VIEW_FACING)
        marker.pose.position.x = float(x)
        marker.pose.position.y = float(y)
        marker.pose.position.z = float(z)
        marker.scale.z = float(scale)
        marker.text = text
        self.set_color(marker, *color)
        return marker

    def add_static_arena_markers(self, markers):
        """
        Static markers use ROS map coordinates:
        ROS x = Minecraft X
        ROS y = Minecraft Z
        ROS z = Minecraft Y
        """

        # Waypoint pads.
        markers.append(self.make_cylinder(100, 'waypoints', 0, 0, 4.25, 3.0, 3.0, 0.25, (1.0, 0.75, 0.0, 0.85)))
        markers.append(self.make_text(101, 'labels', 0, 0, 5.2, 'HOME / TAKEOFF', 0.8, (1.0, 1.0, 1.0, 1.0)))

        markers.append(self.make_cylinder(102, 'waypoints', 10, 0, 4.25, 3.0, 3.0, 0.25, (1.0, 0.0, 0.0, 0.85)))
        markers.append(self.make_text(103, 'labels', 10, 0, 5.2, 'REDSTONE WP', 0.8, (1.0, 1.0, 1.0, 1.0)))

        markers.append(self.make_cylinder(104, 'waypoints', 10, 10, 4.25, 3.0, 3.0, 0.25, (0.0, 1.0, 0.0, 0.85)))
        markers.append(self.make_text(105, 'labels', 10, 10, 5.2, 'EMERALD WP', 0.8, (1.0, 1.0, 1.0, 1.0)))

        markers.append(self.make_cylinder(106, 'waypoints', 0, 10, 4.25, 3.0, 3.0, 0.25, (0.0, 0.25, 1.0, 0.85)))
        markers.append(self.make_text(107, 'labels', 0, 10, 5.2, 'LAPIS WP', 0.8, (1.0, 1.0, 1.0, 1.0)))

        # Inspection target.
        markers.append(self.make_cube(120, 'inspection', 19, 19, 6.5, 4.0, 4.0, 5.0, (0.0, 1.0, 0.2, 0.45)))
        markers.append(self.make_text(121, 'labels', 19, 19, 10.0, 'INSPECTION TARGET', 0.9, (0.2, 1.0, 0.2, 1.0)))

        # Obstacles from map_builder_node/world_setup_node.
        # Each tuple: x_min, x_max, z_min, z_max, y_min, y_max
        obstacles = [
            (4.0, 6.0, -8.0, 6.0, 5.0, 14.0),
            (9.0, 18.0, 3.0, 5.0, 5.0, 14.0),
            (14.0, 16.0, 8.0, 16.0, 5.0, 14.0),
            (-8.0, -5.0, 4.0, 18.0, 5.0, 13.0),
            (18.0, 20.0, -12.0, -10.0, 5.0, 13.0),
            (-16.0, -14.0, -16.0, -14.0, 5.0, 12.0),
            (-18.0, -16.0, 8.0, 10.0, 5.0, 11.0),
            (2.0, 4.0, 18.0, 20.0, 5.0, 12.0),
            (20.0, 22.0, 5.0, 7.0, 5.0, 12.0),
        ]

        marker_id = 200
        for x_min, x_max, z_min, z_max, y_min, y_max in obstacles:
            center_x = (x_min + x_max) / 2.0
            center_y = (z_min + z_max) / 2.0
            center_z = (y_min + y_max) / 2.0

            sx = max(0.5, x_max - x_min + 1.0)
            sy = max(0.5, z_max - z_min + 1.0)
            sz = max(0.5, y_max - y_min + 1.0)

            markers.append(
                self.make_cube(
                    marker_id,
                    'obstacles',
                    center_x,
                    center_y,
                    center_z,
                    sx,
                    sy,
                    sz,
                    (0.85, 0.1, 0.1, 0.35),
                )
            )
            marker_id += 1

    def add_dynamic_markers(self, markers):
        if self.last_drone_pose is not None:
            p = self.last_drone_pose.pose.position
            markers.append(
                self.make_sphere(
                    1,
                    'drone',
                    p.x,
                    p.y,
                    p.z,
                    1.2,
                    (0.0, 0.8, 1.0, 1.0),
                )
            )
            markers.append(
                self.make_text(
                    2,
                    'labels',
                    p.x,
                    p.y,
                    p.z + 1.6,
                    'ALLAY DRONE',
                    0.8,
                    (0.0, 0.9, 1.0, 1.0),
                )
            )

        if self.last_target is not None:
            p = self.last_target.pose.position
            markers.append(
                self.make_sphere(
                    10,
                    'current_target',
                    p.x,
                    p.y,
                    p.z,
                    0.8,
                    (1.0, 1.0, 0.0, 0.95),
                )
            )
            markers.append(
                self.make_text(
                    11,
                    'labels',
                    p.x,
                    p.y,
                    p.z + 1.2,
                    'CURRENT TARGET',
                    0.6,
                    (1.0, 1.0, 0.0, 1.0),
                )
            )

        if self.last_goal is not None:
            p = self.last_goal.pose.position
            markers.append(
                self.make_cylinder(
                    20,
                    'mission_goal',
                    p.x,
                    p.y,
                    p.z,
                    1.5,
                    1.5,
                    1.0,
                    (0.3, 1.0, 0.3, 0.75),
                )
            )
            markers.append(
                self.make_text(
                    21,
                    'labels',
                    p.x,
                    p.y,
                    p.z + 1.5,
                    'MISSION GOAL',
                    0.7,
                    (0.4, 1.0, 0.4, 1.0),
                )
            )

    def timer_callback(self):
        marker_array = MarkerArray()
        markers = []

        self.add_static_arena_markers(markers)
        self.add_dynamic_markers(markers)

        marker_array.markers = markers
        self.marker_pub.publish(marker_array)

        status = String()
        status.data = (
            f'visualizer markers published: count={len(markers)}, '
            f'drone_pose={self.last_drone_pose is not None}, '
            f'target={self.last_target is not None}, '
            f'goal={self.last_goal is not None}'
        )
        self.status_pub.publish(status)


def main(args=None):
    rclpy.init(args=args)
    node = VisualizerNode()

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
