import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
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

    return LaunchDescription([
        map_builder,
    ])
