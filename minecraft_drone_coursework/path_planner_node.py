import heapq
import math
import time
from collections import deque

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, HistoryPolicy

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid, Path
from std_msgs.msg import String


class AStarPathPlannerNode(Node):
    """
    A* path planner for the Minecraft drone coursework.

    Subscribes:
    - /drone/local_map : nav_msgs/OccupancyGrid
    - /drone/pose      : geometry_msgs/PoseStamped
    - /drone/goal      : geometry_msgs/PoseStamped

    Publishes:
    - /drone/planned_path    : nav_msgs/Path
    - /drone/target          : geometry_msgs/PoseStamped
    - /drone/planner_status  : std_msgs/String

    Coordinate convention:
    - ROS x = Minecraft X
    - ROS y = Minecraft Z
    - ROS z = Minecraft Y / altitude

    The planner builds a 2D path in x-y and keeps target altitude from /drone/goal.
    """

    def __init__(self):
        super().__init__('path_planner_node')

        self.declare_parameter('map_topic', '/drone/local_map')
        self.declare_parameter('pose_topic', '/drone/pose')
        self.declare_parameter('goal_topic', '/drone/goal')

        self.declare_parameter('planned_path_topic', '/drone/planned_path')
        self.declare_parameter('target_topic', '/drone/target')
        self.declare_parameter('status_topic', '/drone/planner_status')

        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('planner_rate', 5.0)
        self.declare_parameter('replan_period_sec', 1.0)

        self.declare_parameter('occupied_threshold', 50)
        self.declare_parameter('goal_tolerance', 0.6)
        self.declare_parameter('lookahead_distance', 2.0)
        self.declare_parameter('default_flight_altitude', 10.0)

        self.map_topic = self.get_parameter('map_topic').value
        self.pose_topic = self.get_parameter('pose_topic').value
        self.goal_topic = self.get_parameter('goal_topic').value

        self.planned_path_topic = self.get_parameter('planned_path_topic').value
        self.target_topic = self.get_parameter('target_topic').value
        self.status_topic = self.get_parameter('status_topic').value

        self.frame_id = self.get_parameter('frame_id').value
        self.planner_rate = float(self.get_parameter('planner_rate').value)
        self.replan_period_sec = float(self.get_parameter('replan_period_sec').value)

        self.occupied_threshold = int(self.get_parameter('occupied_threshold').value)
        self.goal_tolerance = float(self.get_parameter('goal_tolerance').value)
        self.lookahead_distance = float(self.get_parameter('lookahead_distance').value)
        self.default_flight_altitude = float(
            self.get_parameter('default_flight_altitude').value
        )

        map_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        self.create_subscription(
            OccupancyGrid,
            self.map_topic,
            self.map_callback,
            map_qos,
        )

        self.create_subscription(
            PoseStamped,
            self.pose_topic,
            self.pose_callback,
            10,
        )

        self.create_subscription(
            PoseStamped,
            self.goal_topic,
            self.goal_callback,
            10,
        )

        self.path_pub = self.create_publisher(Path, self.planned_path_topic, 10)
        self.target_pub = self.create_publisher(PoseStamped, self.target_topic, 10)
        self.status_pub = self.create_publisher(String, self.status_topic, 10)

        self.map_msg = None
        self.pose_msg = None
        self.goal_msg = None

        self.path_points = []
        self.path_msg = None

        self.need_replan = True
        self.last_replan_time = 0.0
        self.last_goal_key = None

        self.timer = self.create_timer(
            1.0 / self.planner_rate,
            self.timer_callback,
        )

        self.get_logger().info('A* path planner started')
        self.get_logger().info(f'Map topic: {self.map_topic}')
        self.get_logger().info(f'Pose topic: {self.pose_topic}')
        self.get_logger().info(f'Goal topic: {self.goal_topic}')
        self.get_logger().info(f'Publishing planned path to: {self.planned_path_topic}')
        self.get_logger().info(f'Publishing controller target to: {self.target_topic}')

    def map_callback(self, msg: OccupancyGrid):
        self.map_msg = msg
        self.need_replan = True
        self.publish_status(
            f'MAP_RECEIVED: size={msg.info.width}x{msg.info.height}, '
            f'resolution={msg.info.resolution:.2f}'
        )

    def pose_callback(self, msg: PoseStamped):
        self.pose_msg = msg

    def goal_callback(self, msg: PoseStamped):
        self.goal_msg = msg

        goal_key = (
            round(msg.pose.position.x, 2),
            round(msg.pose.position.y, 2),
            round(msg.pose.position.z, 2),
        )

        if goal_key != self.last_goal_key:
            self.last_goal_key = goal_key
            self.need_replan = True
            self.get_logger().info(
                f'New goal received: x={goal_key[0]:.2f}, y={goal_key[1]:.2f}, z={goal_key[2]:.2f}'
            )

    def timer_callback(self):
        if self.map_msg is None:
            self.publish_status('WAITING_FOR_LOCAL_MAP')
            return

        if self.pose_msg is None:
            self.publish_status('WAITING_FOR_DRONE_POSE')
            return

        if self.goal_msg is None:
            self.publish_status('WAITING_FOR_GOAL')
            return

        goal_distance = self.distance_2d_pose_to_goal(self.pose_msg, self.goal_msg)

        if goal_distance <= self.goal_tolerance:
            self.publish_target(self.goal_msg.pose.position.x,
                                self.goal_msg.pose.position.y,
                                self.goal_altitude())
            self.publish_status(f'GOAL_REACHED: distance={goal_distance:.2f}')
            return

        now = time.monotonic()
        should_replan = (
            self.need_replan
            or not self.path_points
            or now - self.last_replan_time >= self.replan_period_sec
        )

        if should_replan:
            ok = self.plan_path()

            if not ok:
                self.publish_status('PLANNING_FAILED')
                return

            self.need_replan = False
            self.last_replan_time = now

        self.publish_path()
        self.publish_next_target()

    def plan_path(self) -> bool:
        start_grid = self.world_to_grid(
            self.pose_msg.pose.position.x,
            self.pose_msg.pose.position.y,
        )

        goal_grid = self.world_to_grid(
            self.goal_msg.pose.position.x,
            self.goal_msg.pose.position.y,
        )

        start_grid = self.nearest_free_cell(start_grid)
        goal_grid = self.nearest_free_cell(goal_grid)

        if start_grid is None:
            self.get_logger().error('No free start cell found')
            return False

        if goal_grid is None:
            self.get_logger().error('No free goal cell found')
            return False

        grid_path = self.astar(start_grid, goal_grid)

        if not grid_path:
            self.get_logger().warn(
                f'A* failed: start={start_grid}, goal={goal_grid}'
            )
            self.path_points = []
            return False

        self.path_points = [
            self.grid_to_world(gx, gy)
            for gx, gy in grid_path
        ]

        self.path_msg = self.build_path_msg(self.path_points, self.goal_altitude())

        self.get_logger().info(
            f'A* path planned: cells={len(grid_path)}, '
            f'start={start_grid}, goal={goal_grid}'
        )

        return True

    def astar(self, start, goal):
        open_heap = []
        heapq.heappush(open_heap, (0.0, start))

        came_from = {}
        g_score = {start: 0.0}

        visited = set()

        while open_heap:
            _, current = heapq.heappop(open_heap)

            if current in visited:
                continue

            visited.add(current)

            if current == goal:
                return self.reconstruct_path(came_from, current)

            for neighbor, step_cost in self.neighbors(current):
                if neighbor in visited:
                    continue

                tentative_g = g_score[current] + step_cost

                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + self.heuristic(neighbor, goal)
                    heapq.heappush(open_heap, (f_score, neighbor))

        return []

    def neighbors(self, cell):
        gx, gy = cell

        candidates = [
            (-1, 0, 1.0),
            (1, 0, 1.0),
            (0, -1, 1.0),
            (0, 1, 1.0),
            (-1, -1, math.sqrt(2.0)),
            (-1, 1, math.sqrt(2.0)),
            (1, -1, math.sqrt(2.0)),
            (1, 1, math.sqrt(2.0)),
        ]

        result = []

        for dx, dy, cost in candidates:
            nx = gx + dx
            ny = gy + dy

            if not self.is_free(nx, ny):
                continue

            # Prevent diagonal corner cutting.
            if dx != 0 and dy != 0:
                if not self.is_free(gx + dx, gy):
                    continue
                if not self.is_free(gx, gy + dy):
                    continue

            result.append(((nx, ny), cost))

        return result

    def reconstruct_path(self, came_from, current):
        path = [current]

        while current in came_from:
            current = came_from[current]
            path.append(current)

        path.reverse()
        return path

    def heuristic(self, a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def nearest_free_cell(self, cell):
        if self.is_free(cell[0], cell[1]):
            return cell

        queue = deque([cell])
        visited = {cell}

        max_radius = 10

        while queue:
            current = queue.popleft()
            cx, cy = current

            if abs(cx - cell[0]) > max_radius or abs(cy - cell[1]) > max_radius:
                continue

            for dx, dy, _ in [
                (-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1),
                (-1, -1, 1), (-1, 1, 1), (1, -1, 1), (1, 1, 1),
            ]:
                nxt = (cx + dx, cy + dy)

                if nxt in visited:
                    continue

                visited.add(nxt)

                if self.is_free(nxt[0], nxt[1]):
                    return nxt

                if self.in_grid(nxt[0], nxt[1]):
                    queue.append(nxt)

        return None

    def world_to_grid(self, x, y):
        info = self.map_msg.info
        origin_x = info.origin.position.x
        origin_y = info.origin.position.y
        resolution = info.resolution

        gx = int(round((x - origin_x) / resolution))
        gy = int(round((y - origin_y) / resolution))

        gx = max(0, min(info.width - 1, gx))
        gy = max(0, min(info.height - 1, gy))

        return gx, gy

    def grid_to_world(self, gx, gy):
        info = self.map_msg.info
        origin_x = info.origin.position.x
        origin_y = info.origin.position.y
        resolution = info.resolution

        x = origin_x + gx * resolution
        y = origin_y + gy * resolution

        return (x, y)

    def in_grid(self, gx, gy):
        info = self.map_msg.info
        return 0 <= gx < info.width and 0 <= gy < info.height

    def is_free(self, gx, gy):
        if not self.in_grid(gx, gy):
            return False

        index = gy * self.map_msg.info.width + gx
        value = self.map_msg.data[index]

        if value < 0:
            return False

        return value < self.occupied_threshold

    def build_path_msg(self, points, altitude):
        msg = Path()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id

        for x, y in points:
            pose = PoseStamped()
            pose.header.stamp = msg.header.stamp
            pose.header.frame_id = self.frame_id
            pose.pose.position.x = float(x)
            pose.pose.position.y = float(y)
            pose.pose.position.z = float(altitude)
            pose.pose.orientation.w = 1.0
            msg.poses.append(pose)

        return msg

    def publish_path(self):
        if self.path_msg is None:
            return

        self.path_msg.header.stamp = self.get_clock().now().to_msg()

        for pose in self.path_msg.poses:
            pose.header.stamp = self.path_msg.header.stamp

        self.path_pub.publish(self.path_msg)

    def publish_next_target(self):
        if not self.path_points:
            return

        current_x = self.pose_msg.pose.position.x
        current_y = self.pose_msg.pose.position.y

        closest_index = 0
        closest_distance = float('inf')

        for i, (x, y) in enumerate(self.path_points):
            dist = math.hypot(x - current_x, y - current_y)

            if dist < closest_distance:
                closest_distance = dist
                closest_index = i

        target_index = len(self.path_points) - 1

        for i in range(closest_index, len(self.path_points)):
            x, y = self.path_points[i]
            dist = math.hypot(x - current_x, y - current_y)

            if dist >= self.lookahead_distance:
                target_index = i
                break

        target_x, target_y = self.path_points[target_index]
        altitude = self.goal_altitude()

        self.publish_target(target_x, target_y, altitude)

        final_goal_distance = self.distance_2d_pose_to_goal(self.pose_msg, self.goal_msg)

        self.publish_status(
            f'FOLLOWING_ASTAR_PATH: path_points={len(self.path_points)}, '
            f'closest_index={closest_index}, target_index={target_index}, '
            f'goal_distance={final_goal_distance:.2f}'
        )

    def publish_target(self, x, y, altitude):
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id

        msg.pose.position.x = float(x)
        msg.pose.position.y = float(y)
        msg.pose.position.z = float(altitude)
        msg.pose.orientation.w = 1.0

        self.target_pub.publish(msg)

    def goal_altitude(self):
        altitude = self.goal_msg.pose.position.z

        if abs(altitude) < 1e-6:
            altitude = self.default_flight_altitude

        return altitude

    def distance_2d_pose_to_goal(self, pose_msg, goal_msg):
        return math.hypot(
            pose_msg.pose.position.x - goal_msg.pose.position.x,
            pose_msg.pose.position.y - goal_msg.pose.position.y,
        )

    def publish_status(self, text: str):
        msg = String()
        msg.data = text
        self.status_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = AStarPathPlannerNode()

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
