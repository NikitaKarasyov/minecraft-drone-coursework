import os
from glob import glob

from setuptools import setup

package_name = 'minecraft_drone_coursework'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'rviz'), glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='nikita',
    maintainer_email='nikita@example.com',
    description='ROS 2 Minecraft drone patrol coursework MVP',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'world_setup_node = minecraft_drone_coursework.world_setup_node:main',
            'drone_spawn_node = minecraft_drone_coursework.drone_spawn_node:main',
            'drone_entity_controller_node = minecraft_drone_coursework.drone_entity_controller_node:main',
            'mission_planner_node = minecraft_drone_coursework.mission_planner_node:main',
            'map_builder_node = minecraft_drone_coursework.map_builder_node:main',
            'path_planner_node = minecraft_drone_coursework.path_planner_node:main',
            'visualizer_node = minecraft_drone_coursework.visualizer_node:main',
            'player_camera_follow_node = minecraft_drone_coursework.player_camera_follow_node:main',
            'lidar_processor_node = minecraft_drone_coursework.lidar_processor_node:main',
            'mission_controller_node = minecraft_drone_coursework.mission_controller_node:main',
            'waypoint_square_controller_node = minecraft_drone_coursework.waypoint_square_controller_node:main',
            'sensor_monitor_node = minecraft_drone_coursework.sensor_monitor_node:main',
        ],
    },
)
