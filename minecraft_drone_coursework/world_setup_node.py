import time

import rclpy
from rclpy.node import Node
from minecraft_msgs.srv import Command


class WorldSetupNode(Node):
    """
    Prepares a Minecraft test field for the ROS 2 drone coursework.

    The node creates:
    - flat arena platform;
    - colored waypoint markers;
    - takeoff pad;
    - inspection target;
    - simple obstacles;
    - clean weather/daytime settings.

    The visible drone entity will be created later by drone_spawn_node.
    """

    def __init__(self):
        super().__init__('world_setup_node')

        self.declare_parameter('service_name', '/minecraft/command')
        self.declare_parameter('setup_delay_sec', 0.25)

        self.service_name = self.get_parameter('service_name').value
        self.setup_delay_sec = float(self.get_parameter('setup_delay_sec').value)

        self.client = self.create_client(Command, self.service_name)

    def call_command(self, command: str) -> bool:
        request = Command.Request()
        request.command = command

        self.get_logger().info(f'Executing Minecraft command: {command}')

        future = self.client.call_async(request)
        rclpy.spin_until_future_complete(self, future)

        if future.result() is None:
            self.get_logger().error(f'No response for command: {command}')
            return False

        response = future.result()

        if response.success:
            self.get_logger().info(f'Success: {response.message}')
        else:
            self.get_logger().warn(f'Command returned failure: {response.message}')

        return bool(response.success)

    def setup_world(self):
        self.get_logger().info(f'Waiting for service {self.service_name}...')

        if not self.client.wait_for_service(timeout_sec=15.0):
            self.get_logger().error(f'Service {self.service_name} is not available')
            return

        commands = [
            # ----------------------------
            # Basic world settings
            # ----------------------------
            'time set day',
            'weather clear',
            'difficulty peaceful',
            'gamerule doMobSpawning false',
            'gamerule doDaylightCycle false',
            'gamerule doWeatherCycle false',
            'gamemode creative @p',

            # Put the player above the arena center.
            'tp @p 0 8 0',

            # Remove old drone entities from previous runs.
            'kill @e[tag=ros_drone]',
            'kill @e[tag=ros_target]',

            # ----------------------------
            # Clear flight volume
            # Split into two fill commands to avoid Minecraft fill block limit.
            # Arena: x=[-25,25], z=[-25,25], y=[4,18]
            # ----------------------------
            'fill -25 5 -25 25 11 25 minecraft:air',
            'fill -25 12 -25 25 18 25 minecraft:air',

            # ----------------------------
            # Main flat platform
            # ----------------------------
            'fill -25 4 -25 25 4 25 minecraft:smooth_stone',

            # ----------------------------
            # Arena boundary
            # ----------------------------
            'fill -25 5 -25 25 5 -25 minecraft:blue_concrete',
            'fill -25 5 25 25 5 25 minecraft:blue_concrete',
            'fill -25 5 -25 -25 5 25 minecraft:blue_concrete',
            'fill 25 5 -25 25 5 25 minecraft:blue_concrete',

            # ----------------------------
            # Takeoff/start pad: gold
            # Center: (0, 4, 0)
            # ----------------------------
            'fill -2 4 -2 2 4 2 minecraft:gold_block',

            # ----------------------------
            # Waypoint pads matching the planned square route
            # WP1: redstone   at (10, 4, 0)
            # WP2: emerald    at (10, 4, 10)
            # WP3: lapis      at (0, 4, 10)
            # Home: gold      at (0, 4, 0)
            # ----------------------------
            'fill 8 4 -2 12 4 2 minecraft:redstone_block',
            'fill 8 4 8 12 4 12 minecraft:emerald_block',
            'fill -2 4 8 2 4 12 minecraft:lapis_block',

            # Center marker for visual reference.
            'fill 4 4 4 6 4 6 minecraft:diamond_block',

            # ----------------------------
            # Inspection target area
            # This is the "object of interest" for the drone mission.
            # ----------------------------
            'fill 17 4 17 21 4 21 minecraft:white_concrete',
            'fill 18 5 18 20 7 20 minecraft:green_concrete',
            'setblock 19 8 19 minecraft:beacon',

            # ----------------------------
            # Obstacles / no-fly zones for A* path planning demonstration
            #
            # These obstacles are intentionally arranged as barriers.
            # They block direct straight-line routes between mission goals,
            # so A* has to build visible detours.
            # ----------------------------

            # Wall A: blocks direct route from home/gold to redstone waypoint.
            # Minecraft horizontal footprint: x=[4,6], z=[-8,6]
            'fill 4 5 -8 6 13 6 minecraft:stone_bricks',
            'fill 4 14 -8 6 14 6 minecraft:red_concrete',

            # Wall B: blocks direct route from redstone to emerald.
            # Footprint: x=[9,18], z=[3,5]
            'fill 9 5 3 18 13 5 minecraft:stone_bricks',
            'fill 9 14 3 18 14 5 minecraft:red_concrete',

            # Wall C: blocks part of the route toward the inspection target.
            # Footprint: x=[14,16], z=[8,16]
            'fill 14 5 8 16 13 16 minecraft:stone_bricks',
            'fill 14 14 8 16 14 16 minecraft:red_concrete',

            # Wall D: additional side obstacle for map richness.
            # Footprint: x=[-8,-5], z=[4,18]
            'fill -8 5 4 -5 12 18 minecraft:stone_bricks',
            'fill -8 13 4 -5 13 18 minecraft:red_concrete',

            # Scattered obstacle pillars.
            'fill 18 5 -12 20 12 -10 minecraft:stone_bricks',
            'setblock 19 13 -11 minecraft:red_concrete',

            'fill -16 5 -16 -14 11 -14 minecraft:stone_bricks',
            'setblock -15 12 -15 minecraft:red_concrete',

            'fill -18 5 8 -16 10 10 minecraft:stone_bricks',
            'setblock -17 11 9 minecraft:red_concrete',

            'fill 2 5 18 4 11 20 minecraft:stone_bricks',
            'setblock 3 12 19 minecraft:red_concrete',

            'fill 20 5 5 22 11 7 minecraft:stone_bricks',
            'setblock 21 12 6 minecraft:red_concrete',

            # ----------------------------
            # Put player to a convenient observation point
            # ----------------------------
            'tp @p -8 8 -12',
        ]

        success_count = 0

        for command in commands:
            if self.call_command(command):
                success_count += 1
            time.sleep(self.setup_delay_sec)

        self.get_logger().info(
            f'World setup completed: {success_count}/{len(commands)} commands succeeded'
        )
        self.get_logger().info('Arena layout:')
        self.get_logger().info('  gold pad      : takeoff/home')
        self.get_logger().info('  redstone pad  : waypoint 1')
        self.get_logger().info('  emerald pad   : waypoint 2')
        self.get_logger().info('  lapis pad     : waypoint 3')
        self.get_logger().info('  green/beacon  : inspection target')
        self.get_logger().info('  stone pillars : obstacles for future LiDAR safety')


def main(args=None):
    rclpy.init(args=args)
    node = WorldSetupNode()

    try:
        node.setup_world()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
