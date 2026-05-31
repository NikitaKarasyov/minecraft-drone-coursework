import math
import time
from enum import Enum

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String


class MissionState(Enum):
    WAIT_FOR_DRONE = 'WAIT_FOR_DRONE'
    TAKEOFF = 'TAKEOFF'
    PATROL_REDSTONE = 'PATROL_REDSTONE'
    PATROL_EMERALD = 'PATROL_EMERALD'
    PATROL_LAPIS = 'PATROL_LAPIS'
    GO_TO_INSPECTION = 'GO_TO_INSPECTION'
    INSPECT = 'INSPECT'
    RETURN_HOME = 'RETURN_HOME'
    LAND = 'LAND'
    DONE = 'DONE'


def distance_3d_pose_to_target(pose_msg: PoseStamped, target_ros_xyz) -> float:
    px = pose_msg.pose.position.x
    py = pose_msg.pose.position.y
    pz = pose_msg.pose.position.z

    tx, ty, tz = target_ros_xyz

    return math.sqrt(
        (px - tx) ** 2 +
        (py - ty) ** 2 +
        (pz - tz) ** 2
    )


class MissionPlannerNode(Node):
    """
    High-level mission planner for the Allay drone.

    This node does NOT control the drone directly.

    It publishes high-level goals to:
    - /drone/goal

    Then path_planner_node builds an A* path to that goal and publishes
    intermediate targets to:
    - /drone/target

    Mission state machine:

        WAIT_FOR_DRONE
        → TAKEOFF
        → PATROL_REDSTONE
        → PATROL_EMERALD
        → PATROL_LAPIS
        → GO_TO_INSPECTION
        → INSPECT
        → RETURN_HOME
        → LAND
        → DONE
    """

    def __init__(self):
        super().__init__('mission_planner_node')

        self.declare_parameter('drone_pose_topic', '/drone/pose')
        self.declare_parameter('goal_topic', '/drone/goal')
        self.declare_parameter('status_topic', '/drone/status')
        self.declare_parameter('mission_state_topic', '/drone/mission_state')

        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('planner_rate', 2.0)
        self.declare_parameter('goal_tolerance', 0.75)

        # Mission coordinates are given in Minecraft coordinates:
        # X = horizontal, Y = altitude, Z = horizontal.
        self.declare_parameter('home_x', 0.0)
        self.declare_parameter('home_y', 8.0)
        self.declare_parameter('home_z', 0.0)

        self.declare_parameter('flight_y', 10.0)
        self.declare_parameter('landing_y', 6.0)

        self.declare_parameter('redstone_x', 10.0)
        self.declare_parameter('redstone_z', 0.0)

        self.declare_parameter('emerald_x', 10.0)
        self.declare_parameter('emerald_z', 10.0)

        self.declare_parameter('lapis_x', 0.0)
        self.declare_parameter('lapis_z', 10.0)

        self.declare_parameter('inspect_x', 19.0)
        self.declare_parameter('inspect_y', 10.0)
        self.declare_parameter('inspect_z', 19.0)

        self.declare_parameter('inspect_duration_sec', 5.0)

        self.drone_pose_topic = self.get_parameter('drone_pose_topic').value
        self.goal_topic = self.get_parameter('goal_topic').value
        self.status_topic = self.get_parameter('status_topic').value
        self.mission_state_topic = self.get_parameter('mission_state_topic').value

        self.frame_id = self.get_parameter('frame_id').value
        self.planner_rate = float(self.get_parameter('planner_rate').value)
        self.goal_tolerance = float(self.get_parameter('goal_tolerance').value)

        self.home_x = float(self.get_parameter('home_x').value)
        self.home_y = float(self.get_parameter('home_y').value)
        self.home_z = float(self.get_parameter('home_z').value)

        self.flight_y = float(self.get_parameter('flight_y').value)
        self.landing_y = float(self.get_parameter('landing_y').value)

        self.redstone_x = float(self.get_parameter('redstone_x').value)
        self.redstone_z = float(self.get_parameter('redstone_z').value)

        self.emerald_x = float(self.get_parameter('emerald_x').value)
        self.emerald_z = float(self.get_parameter('emerald_z').value)

        self.lapis_x = float(self.get_parameter('lapis_x').value)
        self.lapis_z = float(self.get_parameter('lapis_z').value)

        self.inspect_x = float(self.get_parameter('inspect_x').value)
        self.inspect_y = float(self.get_parameter('inspect_y').value)
        self.inspect_z = float(self.get_parameter('inspect_z').value)

        self.inspect_duration_sec = float(
            self.get_parameter('inspect_duration_sec').value
        )

        self.last_pose = None

        self.state = MissionState.WAIT_FOR_DRONE
        self.state_start_time = time.monotonic()

        self.goal_pub = self.create_publisher(PoseStamped, self.goal_topic, 10)
        self.status_pub = self.create_publisher(String, self.status_topic, 10)
        self.state_pub = self.create_publisher(String, self.mission_state_topic, 10)

        self.create_subscription(
            PoseStamped,
            self.drone_pose_topic,
            self.pose_callback,
            10,
        )

        self.timer = self.create_timer(
            1.0 / self.planner_rate,
            self.timer_callback,
        )

        self.get_logger().info('A*-aware mission planner started')
        self.get_logger().info(f'Drone pose topic: {self.drone_pose_topic}')
        self.get_logger().info(f'Goal topic: {self.goal_topic}')
        self.get_logger().info('Mission will publish semantic goals; A* planner will build safe paths.')

    def pose_callback(self, msg: PoseStamped):
        self.last_pose = msg

    def mc_to_ros_target(self, mc_x, mc_y, mc_z):
        """
        Convert Minecraft coordinates to project ROS coordinates:

        ROS x = Minecraft X
        ROS y = Minecraft Z
        ROS z = Minecraft Y
        """
        return (mc_x, mc_z, mc_y)

    def make_goal_msg(self, target_ros_xyz):
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id

        msg.pose.position.x = target_ros_xyz[0]
        msg.pose.position.y = target_ros_xyz[1]
        msg.pose.position.z = target_ros_xyz[2]
        msg.pose.orientation.w = 1.0

        return msg

    def publish_goal(self, target_ros_xyz):
        msg = self.make_goal_msg(target_ros_xyz)
        self.goal_pub.publish(msg)

    def publish_status(self, text: str):
        msg = String()
        msg.data = text
        self.status_pub.publish(msg)

    def publish_state(self):
        msg = String()
        msg.data = self.state.value
        self.state_pub.publish(msg)

    def set_state(self, new_state: MissionState):
        if new_state == self.state:
            return

        self.get_logger().info(
            f'Mission transition: {self.state.value} → {new_state.value}'
        )
        self.state = new_state
        self.state_start_time = time.monotonic()

    def reached(self, target_ros_xyz) -> bool:
        if self.last_pose is None:
            return False

        dist = distance_3d_pose_to_target(self.last_pose, target_ros_xyz)
        return dist <= self.goal_tolerance

    def distance_to_target(self, target_ros_xyz) -> float:
        if self.last_pose is None:
            return float('inf')

        return distance_3d_pose_to_target(self.last_pose, target_ros_xyz)

    def state_elapsed(self) -> float:
        return time.monotonic() - self.state_start_time

    def timer_callback(self):
        self.publish_state()

        if self.last_pose is None:
            self.publish_status('WAITING_FOR_DRONE_POSE')
            return

        # High-level mission goals in ROS coordinates.
        takeoff = self.mc_to_ros_target(self.home_x, self.flight_y, self.home_z)

        redstone = self.mc_to_ros_target(
            self.redstone_x,
            self.flight_y,
            self.redstone_z,
        )

        emerald = self.mc_to_ros_target(
            self.emerald_x,
            self.flight_y,
            self.emerald_z,
        )

        lapis = self.mc_to_ros_target(
            self.lapis_x,
            self.flight_y,
            self.lapis_z,
        )

        inspect = self.mc_to_ros_target(
            self.inspect_x,
            self.inspect_y,
            self.inspect_z,
        )

        return_home = self.mc_to_ros_target(
            self.home_x,
            self.flight_y,
            self.home_z,
        )

        land = self.mc_to_ros_target(
            self.home_x,
            self.landing_y,
            self.home_z,
        )

        if self.state == MissionState.WAIT_FOR_DRONE:
            self.publish_status('DRONE_POSE_RECEIVED: starting mission')
            self.set_state(MissionState.TAKEOFF)
            return

        if self.state == MissionState.TAKEOFF:
            self.publish_goal(takeoff)
            self.publish_status(
                f'TAKEOFF: goal=home at flight altitude, '
                f'distance={self.distance_to_target(takeoff):.2f}'
            )

            if self.reached(takeoff):
                self.set_state(MissionState.PATROL_REDSTONE)
            return

        if self.state == MissionState.PATROL_REDSTONE:
            self.publish_goal(redstone)
            self.publish_status(
                f'PATROL_REDSTONE: moving to redstone waypoint through A*, '
                f'distance={self.distance_to_target(redstone):.2f}'
            )

            if self.reached(redstone):
                self.set_state(MissionState.PATROL_EMERALD)
            return

        if self.state == MissionState.PATROL_EMERALD:
            self.publish_goal(emerald)
            self.publish_status(
                f'PATROL_EMERALD: moving to emerald waypoint through A*, '
                f'distance={self.distance_to_target(emerald):.2f}'
            )

            if self.reached(emerald):
                self.set_state(MissionState.PATROL_LAPIS)
            return

        if self.state == MissionState.PATROL_LAPIS:
            self.publish_goal(lapis)
            self.publish_status(
                f'PATROL_LAPIS: moving to lapis waypoint through A*, '
                f'distance={self.distance_to_target(lapis):.2f}'
            )

            if self.reached(lapis):
                self.set_state(MissionState.GO_TO_INSPECTION)
            return

        if self.state == MissionState.GO_TO_INSPECTION:
            self.publish_goal(inspect)
            self.publish_status(
                f'GO_TO_INSPECTION: moving to target area through A*, '
                f'distance={self.distance_to_target(inspect):.2f}'
            )

            if self.reached(inspect):
                self.set_state(MissionState.INSPECT)
            return

        if self.state == MissionState.INSPECT:
            self.publish_goal(inspect)
            self.publish_status(
                f'INSPECT: holding position near target, '
                f'elapsed={self.state_elapsed():.1f}/{self.inspect_duration_sec:.1f}s'
            )

            if self.state_elapsed() >= self.inspect_duration_sec:
                self.set_state(MissionState.RETURN_HOME)
            return

        if self.state == MissionState.RETURN_HOME:
            self.publish_goal(return_home)
            self.publish_status(
                f'RETURN_HOME: returning to home through A*, '
                f'distance={self.distance_to_target(return_home):.2f}'
            )

            if self.reached(return_home):
                self.set_state(MissionState.LAND)
            return

        if self.state == MissionState.LAND:
            self.publish_goal(land)
            self.publish_status(
                f'LAND: descending to landing altitude, '
                f'distance={self.distance_to_target(land):.2f}'
            )

            if self.reached(land):
                self.set_state(MissionState.DONE)
            return

        if self.state == MissionState.DONE:
            self.publish_goal(land)
            self.publish_status('DONE: mission completed')
            return


def main(args=None):
    rclpy.init(args=args)
    node = MissionPlannerNode()

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
