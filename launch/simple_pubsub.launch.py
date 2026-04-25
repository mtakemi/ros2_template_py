from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        Node(
            package='ros2_template_py',
            executable='simple_publisher',
            name='simple_publisher',
            output='screen',
        ),
        Node(
            package='ros2_template_py',
            executable='simple_subscriber',
            name='simple_subscriber',
            output='screen',
        ),
    ])
