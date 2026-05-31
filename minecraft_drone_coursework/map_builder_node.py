import math

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, HistoryPolicy

from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import String


class MapBuilderNode(Node):
    """
    Builds a simple 2D occupancy grid map for the Minecraft drone arena.

    The map is based on known arena geometry created by world_setup_node.

    Coordinate convention:
    - Minecraft X -> ROS map X
    - Minecraft Z -> ROS map Y
    - Minecraft Y is altitude and is not used in the 2D map

    OccupancyGrid:
    - 0   = free space
    - 100 = occupied / obstacle / boundary / safety margin
    """

    def __init__(self):
        super().__init__('map_builder_node')

        self.declare_parameter('map_topic', '/drone/local_map')
        self.declare_parameter('status_topic', '/drone/map_status')

        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('resolution', 1.0)

        self.declare_parameter('min_x', -25.0)
        self.declare_parameter('max_x', 25.0)
        self.declare_parameter('min_z', -25.0)
        self.declare_parameter('max_z', 25.0)

        self.declare_parameter('safety_margin_cells', 2)
        self.declare_parameter('publish_rate', 1.0)

        self.map_topic = self.get_parameter('map_topic').value
        self.status_topic = self.get_parameter('status_topic').value
        self.frame_id = self.get_parameter('frame_id').value

        self.resolution = float(self.get_parameter('resolution').value)

        self.min_x = float(self.get_parameter('min_x').value)
        self.max_x = float(self.get_parameter('max_x').value)
        self.min_z = float(self.get_parameter('min_z').value)
        self.max_z = float(self.get_parameter('max_z').value)

        self.safety_margin_cells = int(
            self.get_parameter('safety_margin_cells').value
        )

        self.publish_rate = float(self.get_parameter('publish_rate').value)

        self.width = int(round((self.max_x - self.min_x) / self.resolution)) + 1
        self.height = int(round((self.max_z - self.min_z) / self.resolution)) + 1

        # Known obstacles from world_setup_node.
        # Each rectangle is in Minecraft horizontal coordinates:
        # x_min, x_max, z_min, z_max
        self.obstacles = [
            # Wall A: blocks direct route from home/gold to redstone.
            # Minecraft footprint: x_min, x_max, z_min, z_max
            (4.0, 6.0, -8.0, 6.0),

            # Wall B: blocks direct route from redstone to emerald.
            (9.0, 18.0, 3.0, 5.0),

            # Wall C: blocks part of the route to the inspection target.
            (14.0, 16.0, 8.0, 16.0),

            # Wall D: additional side barrier.
            (-8.0, -5.0, 4.0, 18.0),

            # Scattered obstacle pillars.
            (18.0, 20.0, -12.0, -10.0),
            (-16.0, -14.0, -16.0, -14.0),
            (-18.0, -16.0, 8.0, 10.0),
            (2.0, 4.0, 18.0, 20.0),
            (20.0, 22.0, 5.0, 7.0),
        ]

        # Optional inspection target footprint.
        # We keep it free for navigation, because it is a goal area,
        # not an obstacle. If needed later, we can add a smaller no-fly zone.
        self.inspection_area = (17.0, 21.0, 17.0, 21.0)

        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.map_pub = self.create_publisher(OccupancyGrid, self.map_topic, qos)
        self.status_pub = self.create_publisher(String, self.status_topic, 10)

        self.map_msg = self.build_map()

        self.timer = self.create_timer(
            1.0 / self.publish_rate,
            self.timer_callback,
        )

        self.get_logger().info('Map builder started')
        self.get_logger().info(
            f'Map bounds: x=[{self.min_x}, {self.max_x}], '
            f'z=[{self.min_z}, {self.max_z}], '
            f'resolution={self.resolution}, size={self.width}x{self.height}'
        )
        self.get_logger().info(
            f'Known obstacles: {len(self.obstacles)}, '
            f'safety_margin_cells={self.safety_margin_cells}'
        )
        self.get_logger().info(f'Publishing OccupancyGrid to {self.map_topic}')

    def world_to_grid(self, x: float, z: float):
        gx = int(round((x - self.min_x) / self.resolution))
        gy = int(round((z - self.min_z) / self.resolution))
        return gx, gy

    def grid_to_index(self, gx: int, gy: int) -> int:
        return gy * self.width + gx

    def in_grid(self, gx: int, gy: int) -> bool:
        return 0 <= gx < self.width and 0 <= gy < self.height

    def mark_cell(self, data, gx: int, gy: int, value: int = 100):
        if self.in_grid(gx, gy):
            data[self.grid_to_index(gx, gy)] = value

    def mark_rectangle(self, data, x_min, x_max, z_min, z_max, value: int = 100):
        gx_min, gy_min = self.world_to_grid(x_min, z_min)
        gx_max, gy_max = self.world_to_grid(x_max, z_max)

        if gx_min > gx_max:
            gx_min, gx_max = gx_max, gx_min
        if gy_min > gy_max:
            gy_min, gy_max = gy_max, gy_min

        for gy in range(gy_min, gy_max + 1):
            for gx in range(gx_min, gx_max + 1):
                self.mark_cell(data, gx, gy, value)

    def inflate_obstacles(self, data):
        """
        Inflate occupied cells by safety_margin_cells.

        This creates a safety buffer around obstacles so the drone path does not
        pass too close to pillars.
        """
        if self.safety_margin_cells <= 0:
            return data

        inflated = list(data)
        occupied_indices = [
            index for index, value in enumerate(data)
            if value >= 100
        ]

        for index in occupied_indices:
            gy = index // self.width
            gx = index % self.width

            for dy in range(-self.safety_margin_cells, self.safety_margin_cells + 1):
                for dx in range(-self.safety_margin_cells, self.safety_margin_cells + 1):
                    if math.hypot(dx, dy) <= self.safety_margin_cells:
                        self.mark_cell(inflated, gx + dx, gy + dy, 100)

        return inflated

    def mark_arena_boundary(self, data):
        """
        Mark the outer border as occupied.

        This prevents A* from planning exactly on the boundary.
        """
        for gx in range(self.width):
            self.mark_cell(data, gx, 0, 100)
            self.mark_cell(data, gx, self.height - 1, 100)

        for gy in range(self.height):
            self.mark_cell(data, 0, gy, 100)
            self.mark_cell(data, self.width - 1, gy, 100)

    def build_map(self) -> OccupancyGrid:
        data = [0 for _ in range(self.width * self.height)]

        self.mark_arena_boundary(data)

        for obstacle in self.obstacles:
            self.mark_rectangle(data, *obstacle, value=100)

        data = self.inflate_obstacles(data)

        msg = OccupancyGrid()

        msg.header.frame_id = self.frame_id
        msg.info.resolution = self.resolution
        msg.info.width = self.width
        msg.info.height = self.height

        # OccupancyGrid origin is the world coordinate of cell (0, 0).
        msg.info.origin.position.x = self.min_x
        msg.info.origin.position.y = self.min_z
        msg.info.origin.position.z = 0.0
        msg.info.origin.orientation.w = 1.0

        msg.data = data

        return msg

    def timer_callback(self):
        self.map_msg.header.stamp = self.get_clock().now().to_msg()
        self.map_pub.publish(self.map_msg)

        occupied = sum(1 for value in self.map_msg.data if value >= 100)
        free = sum(1 for value in self.map_msg.data if value == 0)

        status = String()
        status.data = (
            f'local_map published: size={self.width}x{self.height}, '
            f'free={free}, occupied={occupied}, '
            f'safety_margin_cells={self.safety_margin_cells}'
        )
        self.status_pub.publish(status)


def main(args=None):
    rclpy.init(args=args)
    node = MapBuilderNode()

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
