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

    drone_spawn = TimerAction(
        period=4.0,
        actions=[
            Node(
                package=package_name,
                executable='drone_spawn_node',
                name='drone_spawn_node',
                output='screen',
                parameters=[params_file],
            )
        ],
    )

    drone_controller = TimerAction(
        period=6.0,
        actions=[
            Node(
                package=package_name,
                executable='drone_entity_controller_node',
                name='drone_entity_controller_node',
                output='screen',
                parameters=[params_file],
            )
        ],
    )

    mission_planner = TimerAction(
        period=8.0,
        actions=[
            Node(
                package=package_name,
                executable='mission_planner_node',
                name='mission_planner_node',
                output='screen',
                parameters=[params_file],
            )
        ],
    )

    # Optional: keep camera following the drone for a cinematic demonstration.
    camera_follow = TimerAction(
        period=9.0,
        actions=[
            Node(
                package=package_name,
                executable='player_camera_follow_node',
                name='player_camera_follow_node',
                output='screen',
                parameters=[params_file],
            )
        ],
    )

    sensor_monitor = TimerAction(
        period=10.0,
        actions=[
            Node(
                package=package_name,
                executable='sensor_monitor_node',
                name='sensor_monitor_node',
                output='screen',
                parameters=[params_file],
            )
        ],
    )

    return LaunchDescription([
        world_setup,
        drone_spawn,
        drone_controller,
        mission_planner,
        camera_follow,
        sensor_monitor,
    ])
