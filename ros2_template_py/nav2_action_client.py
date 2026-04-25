import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node


class Nav2ActionClient(Node):
    def __init__(self) -> None:
        super().__init__('nav2_action_client')
        self._action_client = ActionClient(
            self, NavigateToPose, 'navigate_to_pose'
        )
        self._process_timer = self.create_timer(1.0, self.on_process_tick)
        self._nav_timer = self.create_timer(60.0, self.send_nav_goal)
        self._is_navigating = False

    # ------------------------------------------------------------------
    # 1 秒周期の自ノード処理（必要に応じて処理を追記）
    # ------------------------------------------------------------------
    def on_process_tick(self) -> None:
        self.get_logger().debug('Process tick')

    # ------------------------------------------------------------------
    # 60 秒周期の Nav2 Goal 送信
    # ------------------------------------------------------------------
    def send_nav_goal(self) -> None:
        if self._is_navigating:
            self.get_logger().warn(
                'Navigation already in progress, skipping goal.'
            )
            return

        if not self._action_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn(
                'NavigateToPose action server not available.'
            )
            return

        goal = NavigateToPose.Goal()
        goal.pose = self._build_goal_pose(x=1.0, y=0.0, w=1.0)

        self.get_logger().info('Sending navigation goal...')
        future = self._action_client.send_goal_async(
            goal,
            feedback_callback=self.on_feedback,
        )
        future.add_done_callback(self.on_goal_response)
        self._is_navigating = True

    def _build_goal_pose(
        self, x: float, y: float, w: float
    ) -> PoseStamped:
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.orientation.w = w
        return pose

    # ------------------------------------------------------------------
    # Action callbacks
    # ------------------------------------------------------------------
    def on_goal_response(self, future) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('Goal rejected.')
            self._is_navigating = False
            return

        self.get_logger().info('Goal accepted.')
        goal_handle.get_result_async().add_done_callback(self.on_result)

    def on_feedback(self, feedback_msg) -> None:
        remaining = feedback_msg.feedback.distance_remaining
        self.get_logger().info(
            f'Distance remaining: {remaining:.2f} m'
        )

    def on_result(self, future) -> None:
        status = future.result().status
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info('Navigation succeeded.')
        else:
            self.get_logger().warn(
                f'Navigation ended with status: {status}'
            )
        self._is_navigating = False


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Nav2ActionClient()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
