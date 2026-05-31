import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import Node


def generate_launch_description():
    package_name = 'minecraft_drone_coursework'

    params_file = os.path.join(
        get_package_share_directory(package_name),
        'config',
        'patrol_params.yaml',
    )

    world_setup = Node(
        package=package_name,
        executable='world_setup_node',
        name='world_setup_node',
        output='screen',
        parameters=[params_file],
    )

    sensor_monitor = Node(
        package=package_name,
        executable='sensor_monitor_node',
        name='sensor_monitor_node',
        output='screen',
        parameters=[params_file],
    )

    mission_controller = TimerAction(
        period=4.0,
        actions=[
            Node(
                package=package_name,
                executable='mission_controller_node',
                name='mission_controller_node',
                output='screen',
                parameters=[params_file],
            )
        ],
    )

    return LaunchDescription([
        world_setup,
        sensor_monitor,
        mission_controller,
    ])
