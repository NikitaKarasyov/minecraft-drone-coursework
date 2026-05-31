import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import Node


def generate_launch_description():
    package_name = 'minecraft_drone_coursework'

    package_share = get_package_share_directory(package_name)

    params_file = os.path.join(
        package_share,
        'config',
        'patrol_params.yaml',
    )

    rviz_config = os.path.join(
        package_share,
        'rviz',
        'minecraft_drone.rviz',
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

    map_builder = TimerAction(
        period=5.0,
        actions=[
            Node(
                package=package_name,
                executable='map_builder_node',
                name='map_builder_node',
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

    path_planner = TimerAction(
        period=7.0,
        actions=[
            Node(
                package=package_name,
                executable='path_planner_node',
                name='path_planner_node',
                output='screen',
                parameters=[params_file],
            )
        ],
    )

    mission_planner = TimerAction(
        period=9.0,
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

    camera_follow = TimerAction(
        period=10.0,
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
        period=11.0,
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

    visualizer = TimerAction(
        period=12.0,
        actions=[
            Node(
                package=package_name,
                executable='visualizer_node',
                name='visualizer_node',
                output='screen',
                parameters=[params_file],
            )
        ],
    )

    rviz = TimerAction(
        period=14.0,
        actions=[
            Node(
                package='rviz2',
                executable='rviz2',
                name='rviz2',
                output='screen',
                arguments=['-d', rviz_config],
            )
        ],
    )

    return LaunchDescription([
        world_setup,
        drone_spawn,
        map_builder,
        drone_controller,
        path_planner,
        mission_planner,
        camera_follow,
        sensor_monitor,
        visualizer,
        rviz,
    ])
