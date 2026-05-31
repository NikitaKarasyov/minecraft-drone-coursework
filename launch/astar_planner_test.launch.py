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

    map_builder = Node(
        package=package_name,
        executable='map_builder_node',
        name='map_builder_node',
        output='screen',
        parameters=[params_file],
    )

    drone_controller = TimerAction(
        period=1.0,
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
        period=2.0,
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

    # Camera follows the Allay drone using /drone/pose.
    # This is for visual demonstration: the player becomes a camera rig.
    camera_follow = TimerAction(
        period=3.0,
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

    return LaunchDescription([
        map_builder,
        drone_controller,
        path_planner,
        camera_follow,
    ])
