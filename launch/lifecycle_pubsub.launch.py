import lifecycle_msgs.msg
from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler
from launch_ros.actions import LifecycleNode
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState


def generate_launch_description() -> LaunchDescription:
    lc_pub = LifecycleNode(
        package='ros2_template_py',
        executable='lifecycle_publisher',
        name='lifecycle_publisher',
        namespace='',
        respawn=True, 
        output='screen',
    )

    lc_sub = LifecycleNode(
        package='ros2_template_py',
        executable='lifecycle_subscriber',
        name='lifecycle_subscriber',
        namespace='',
        respawn=True, 
        output='screen',
    )

    # configure はノード内で自動発行 → inactive 到達を検知して activate
    activate_pub = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=lc_pub,
            goal_state='inactive',
            entities=[
                EmitEvent(event=ChangeState(
                    lifecycle_node_matcher=lambda n: n is lc_pub,
                    transition_id=lifecycle_msgs.msg.Transition.TRANSITION_ACTIVATE,
                )),
            ],
        )
    )

    activate_sub = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=lc_sub,
            goal_state='inactive',
            entities=[
                EmitEvent(event=ChangeState(
                    lifecycle_node_matcher=lambda n: n is lc_sub,
                    transition_id=lifecycle_msgs.msg.Transition.TRANSITION_ACTIVATE,
                )),
            ],
        )
    )

    return LaunchDescription([
        lc_pub,
        lc_sub,
        activate_pub,
        activate_sub,
    ])
