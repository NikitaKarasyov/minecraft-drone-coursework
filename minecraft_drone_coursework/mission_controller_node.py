import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class MissionControllerNode(Node):
    """
    Simple autonomous patrol controller.

    Publishes geometry_msgs/Twist to /cmd_vel.
    The Minecraft player is treated as a simplified virtual drone/agent.

    MVP behavior:
    - wait;
    - move forward;
    - turn left;
    - repeat 4 sides;
    - repeat for configurable loops;
    - robustly stop.
    """

    def __init__(self):
        super().__init__('mission_controller_node')

        self.declare_parameter('cmd_vel_topic', '/cmd_vel')

        # Safer default values for the first MVP test.
        self.declare_parameter('linear_speed', 0.35)
        self.declare_parameter('angular_speed', 0.55)
        self.declare_parameter('forward_duration', 1.6)
        self.declare_parameter('turn_duration', 1.0)
        self.declare_parameter('loops', 1)
        self.declare_parameter('publish_rate', 20.0)
        self.declare_parameter('start_delay_sec', 2.0)

        self.cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self.linear_speed = float(self.get_parameter('linear_speed').value)
        self.angular_speed = float(self.get_parameter('angular_speed').value)
        self.forward_duration = float(self.get_parameter('forward_duration').value)
        self.turn_duration = float(self.get_parameter('turn_duration').value)
        self.loops = int(self.get_parameter('loops').value)
        self.publish_rate = float(self.get_parameter('publish_rate').value)
        self.start_delay_sec = float(self.get_parameter('start_delay_sec').value)

        self.publisher = self.create_publisher(Twist, self.cmd_vel_topic, 10)

        self.actions = [('wait', self.start_delay_sec)]

        for _ in range(self.loops):
            for _ in range(4):
                self.actions.append(('forward', self.forward_duration))
                self.actions.append(('turn_left', self.turn_duration))

        self.actions.append(('stop', 2.0))

        self.current_action_index = 0
        self.action_start_time = time.monotonic()
        self.mission_finished = False

        timer_period = 1.0 / self.publish_rate
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.get_logger().info('Mission controller started')
        self.get_logger().info(f'Publishing to: {self.cmd_vel_topic}')
        self.get_logger().info(
            f'Config: linear_speed={self.linear_speed}, '
            f'angular_speed={self.angular_speed}, '
            f'forward_duration={self.forward_duration}, '
            f'turn_duration={self.turn_duration}, '
            f'loops={self.loops}'
        )

        self.log_current_action()

    def log_current_action(self):
        if self.current_action_index < len(self.actions):
            action_name, duration = self.actions[self.current_action_index]
            self.get_logger().info(
                f'Action {self.current_action_index + 1}/{len(self.actions)}: '
                f'{action_name}, duration={duration:.2f}s'
            )

    def timer_callback(self):
        if self.mission_finished:
            self.publish_stop()
            return

        if self.current_action_index >= len(self.actions):
            self.finish_mission()
            return

        action_name, duration = self.actions[self.current_action_index]
        elapsed = time.monotonic() - self.action_start_time

        if elapsed >= duration:
            self.current_action_index += 1
            self.action_start_time = time.monotonic()

            if self.current_action_index >= len(self.actions):
                self.finish_mission()
            else:
                self.log_current_action()

            return

        msg = Twist()

        if action_name == 'wait':
            pass
        elif action_name == 'forward':
            msg.linear.x = self.linear_speed
        elif action_name == 'turn_left':
            msg.angular.z = self.angular_speed
        elif action_name == 'stop':
            pass
        else:
            self.get_logger().warn(f'Unknown action: {action_name}')

        self.publisher.publish(msg)

    def publish_stop(self):
        self.publisher.publish(Twist())

    def publish_stop_burst(self, duration_sec: float = 1.0, rate_hz: float = 20.0):
        """
        Robust stop: publish zero Twist multiple times.

        A single zero message can be lost when the node is shutting down.
        This method sends zero velocity for a short period.
        """
        self.get_logger().info('Publishing robust stop burst...')

        end_time = time.monotonic() + duration_sec
        sleep_time = 1.0 / rate_hz

        while time.monotonic() < end_time:
            self.publish_stop()
            rclpy.spin_once(self, timeout_sec=0.0)
            time.sleep(sleep_time)

        self.get_logger().info('Stop burst completed')

    def finish_mission(self):
        self.get_logger().info('Mission completed. Sending stop command.')
        self.publish_stop_burst(duration_sec=1.0, rate_hz=20.0)
        self.mission_finished = True


def main(args=None):
    rclpy.init(args=args)
    node = MissionControllerNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Interrupted by user')
    finally:
        node.publish_stop_burst(duration_sec=1.0, rate_hz=20.0)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
