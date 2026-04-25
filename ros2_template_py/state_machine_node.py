import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rcl_interfaces.msg import SetParametersResult
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String
from std_srvs.srv import Trigger
from transitions import Machine


class StateMachineNode(Node):

    _states = ['INIT', 'MOVE', 'MODE1', 'MODE2', 'RETURN']
    _transitions = [
        {'trigger': 'next', 'source': 'INIT',   'dest': 'MOVE'},
        {'trigger': 'next', 'source': 'MOVE',   'dest': 'MODE1'},
        {'trigger': 'next', 'source': 'MODE1',  'dest': 'MODE2'},
        {'trigger': 'next', 'source': 'MODE2',  'dest': 'RETURN'},
        {'trigger': 'reset', 'source': '*',      'dest': 'INIT'},
    ]

    def __init__(self) -> None:
        super().__init__('state_machine_node')
        self._machine = Machine(
            model=self,
            states=StateMachineNode._states,
            transitions=StateMachineNode._transitions,
            initial='INIT',
            ignore_invalid_triggers=True,
        )
        self._publisher = self.create_publisher(String, 'state_output', 10)
        self._publish_timer = None
        self._nav_client = ActionClient(
            self, NavigateToPose, 'navigate_to_pose'
        )
        self._nav_goal_handle = None
        self.create_service(Trigger, '~/next', self.on_next_request)
        self.create_service(Trigger, '~/reset', self.on_reset_request)
        # set_state: ros2 param set /state_machine_node target_state <STATE>
        self.declare_parameter('target_state', '')
        self.add_on_set_parameters_callback(self._on_set_state)
        self.get_logger().info(f'StateMachineNode started. state={self.state}')

    # ------------------------------------------------------------------
    # State entry callbacks (transitions: on_enter_<STATE>)
    # ------------------------------------------------------------------
    def on_enter_INIT(self) -> None:
        self.get_logger().info('[INIT] Entered.')
        self._stop_publish()

    def on_enter_MOVE(self) -> None:
        self.get_logger().info('[MOVE] Entered.')

    def on_enter_MODE1(self) -> None:
        self.get_logger().info('[MODE1] Entered. Starting publish.')
        self._start_publish()

    def on_enter_MODE2(self) -> None:
        self.get_logger().info('[MODE2] Entered. Sending Nav2 goal.')
        self._send_nav_goal(x=1.0, y=0.0, w=1.0)

    def on_exit_MODE2(self) -> None:
        self._cancel_nav_goal()
        self.get_logger().info('[MODE2] Exited. Nav2 goal cancelled if active.')

    def on_enter_RETURN(self) -> None:
        self.get_logger().info('[RETURN] Entered. Stopping publish.')
        self._stop_publish()

    # ------------------------------------------------------------------
    # Publish control
    # ------------------------------------------------------------------
    def _start_publish(self) -> None:
        if self._publish_timer is None:
            self._publish_timer = self.create_timer(1.0, self._on_publish_tick)

    def _stop_publish(self) -> None:
        if self._publish_timer is not None:
            self._publish_timer.cancel()
            self._publish_timer = None

    def _on_publish_tick(self) -> None:
        msg = String()
        msg.data = f'state: {self.state}'
        self._publisher.publish(msg)
        self.get_logger().info(f'Published: {msg.data}')

    # ------------------------------------------------------------------
    # Nav2 Action
    # ------------------------------------------------------------------
    def _send_nav_goal(self, x: float, y: float, w: float) -> None:
        if not self._nav_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn(
                'NavigateToPose action server not available.'
            )
            return
        goal = NavigateToPose.Goal()
        goal.pose = self._build_pose(x, y, w)
        self.get_logger().info(
            f'Nav2 goal: x={x}, y={y}, w={w}'
        )
        future = self._nav_client.send_goal_async(
            goal, feedback_callback=self._on_nav_feedback
        )
        future.add_done_callback(self._on_nav_goal_response)

    def _build_pose(self, x: float, y: float, w: float) -> PoseStamped:
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.orientation.w = w
        return pose

    def _cancel_nav_goal(self) -> None:
        if self._nav_goal_handle is not None:
            self._nav_goal_handle.cancel_goal_async()
            self._nav_goal_handle = None

    def _on_nav_goal_response(self, future) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('Nav2 goal rejected.')
            return
        self._nav_goal_handle = goal_handle
        self.get_logger().info('Nav2 goal accepted.')
        goal_handle.get_result_async().add_done_callback(
            self._on_nav_result
        )

    def _on_nav_feedback(self, feedback_msg) -> None:
        dist = feedback_msg.feedback.distance_remaining
        self.get_logger().info(
            f'[MODE2] Nav2 distance remaining: {dist:.2f} m'
        )

    def _on_nav_result(self, future) -> None:
        self._nav_goal_handle = None
        status = future.result().status
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info('[MODE2] Nav2 goal succeeded.')
        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().info('[MODE2] Nav2 goal cancelled.')
        else:
            self.get_logger().warn(
                f'[MODE2] Nav2 goal ended with status: {status}'
            )

    # ------------------------------------------------------------------
    # set_state via parameter
    # ------------------------------------------------------------------
    def _on_set_state(
        self, params: list[Parameter]
    ) -> SetParametersResult:
        for param in params:
            if param.name != 'target_state':
                continue
            target = param.value.upper()
            if not target:
                return SetParametersResult(successful=True)
            if target not in self._states:
                reason = (
                    f'Unknown state: "{param.value}". '
                    f'Valid states: {self._states}'
                )
                self.get_logger().error(f'set_state failed: {reason}')
                return SetParametersResult(successful=False, reason=reason)
            if target == self.state:
                return SetParametersResult(successful=True)
            trigger = self._find_trigger_for(self.state, target)
            if trigger is None:
                reason = (
                    f'No direct transition from "{self.state}" '
                    f'to "{target}"'
                )
                self.get_logger().error(f'set_state failed: {reason}')
                return SetParametersResult(successful=False, reason=reason)
            prev = self.state
            getattr(self, trigger)()
            self.get_logger().info(f'set_state: {prev} -> {self.state}')
        return SetParametersResult(successful=True)

    def _find_trigger_for(
        self, source: str, dest: str
    ) -> str | None:
        for trigger, event in self._machine.events.items():
            for transition in event.transitions.get(source, []):
                if transition.dest == dest:
                    return trigger
        return None

    # ------------------------------------------------------------------
    # Service callbacks
    # ------------------------------------------------------------------
    def on_next_request(
        self,
        request: Trigger.Request,
        response: Trigger.Response,
    ) -> Trigger.Response:
        prev = self.state
        if self.can_next():
            self.next()
            response.success = True
            response.message = f'{prev} -> {self.state}'
        else:
            response.success = False
            response.message = f'No transition from {prev} (already RETURN?)'
        self.get_logger().info(f'next: {response.message}')
        return response

    def on_reset_request(
        self,
        request: Trigger.Request,
        response: Trigger.Response,
    ) -> Trigger.Response:
        prev = self.state
        self.reset()
        response.success = True
        response.message = f'{prev} -> {self.state}'
        self.get_logger().info(f'reset: {response.message}')
        return response


def main(args=None) -> None:
    rclpy.init(args=args)
    node = StateMachineNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
