import time

import rclpy
from rclpy.node import Node
from minecraft_msgs.srv import Command


class DroneSpawnNode(Node):
    """
    Spawns a visible Minecraft entity that represents the virtual drone.

    For the coursework we use minecraft:allay as the drone body:
    - it looks like a flying object;
    - it is easy to identify visually;
    - it can be controlled later via Minecraft commands.

    The entity receives tag "ros_drone", so other nodes can move it using:
    /tp @e[tag=ros_drone,limit=1] x y z
    """

    def __init__(self):
        super().__init__('drone_spawn_node')

        self.declare_parameter('service_name', '/minecraft/command')

        self.declare_parameter('drone_tag', 'ros_drone')
        self.declare_parameter('drone_name', 'ROS Drone')
        self.declare_parameter('entity_type', 'minecraft:allay')

        # Spawn position above the gold takeoff pad created by world_setup_node.
        self.declare_parameter('spawn_x', 0.0)
        self.declare_parameter('spawn_y', 8.0)
        self.declare_parameter('spawn_z', 0.0)

        self.declare_parameter('setup_delay_sec', 0.3)
        self.declare_parameter('kill_existing', True)

        self.service_name = self.get_parameter('service_name').value
        self.drone_tag = self.get_parameter('drone_tag').value
        self.drone_name = self.get_parameter('drone_name').value
        self.entity_type = self.get_parameter('entity_type').value

        self.spawn_x = float(self.get_parameter('spawn_x').value)
        self.spawn_y = float(self.get_parameter('spawn_y').value)
        self.spawn_z = float(self.get_parameter('spawn_z').value)

        self.setup_delay_sec = float(self.get_parameter('setup_delay_sec').value)
        self.kill_existing = bool(self.get_parameter('kill_existing').value)

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

    def spawn_drone(self):
        self.get_logger().info(f'Waiting for service {self.service_name}...')

        if not self.client.wait_for_service(timeout_sec=15.0):
            self.get_logger().error(f'Service {self.service_name} is not available')
            return

        commands = []

        if self.kill_existing:
            commands.append(f'kill @e[tag={self.drone_tag}]')

        # JSON text for visible custom name.
        custom_name_json = (
            '{"text":"' + self.drone_name + '",'
            '"color":"aqua",'
            '"bold":true}'
        )

        # Allay is used as a visible drone entity.
        # NoAI prevents it from flying away.
        # NoGravity keeps it in the air.
        # Glowing makes it easier to see during the demo.
        summon_command = (
            f'summon {self.entity_type} '
            f'{self.spawn_x:.2f} {self.spawn_y:.2f} {self.spawn_z:.2f} '
            '{'
            f'Tags:["{self.drone_tag}"],'
            f'CustomName:\'{custom_name_json}\','
            'CustomNameVisible:1b,'
            'NoAI:1b,'
            'NoGravity:1b,'
            'Invulnerable:1b,'
            'PersistenceRequired:1b,'
            'Glowing:1b,'
            'Silent:1b'
            '}'
        )

        commands.append(summon_command)

        # Extra glowing effect in case entity NBT glowing is not immediately visible.
        commands.append(
            f'effect give @e[tag={self.drone_tag},limit=1] minecraft:glowing 999999 1 true'
        )

        success_count = 0

        for command in commands:
            if self.call_command(command):
                success_count += 1
            time.sleep(self.setup_delay_sec)

        self.get_logger().info(
            f'Drone spawn completed: {success_count}/{len(commands)} commands succeeded'
        )
        self.get_logger().info(
            f'Drone entity: {self.entity_type}, tag={self.drone_tag}, '
            f'position=({self.spawn_x:.2f}, {self.spawn_y:.2f}, {self.spawn_z:.2f})'
        )


def main(args=None):
    rclpy.init(args=args)
    node = DroneSpawnNode()

    try:
        node.spawn_drone()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
