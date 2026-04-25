import rclpy
from rclpy.lifecycle import Node, State, TransitionCallbackReturn
from rclpy.lifecycle import Publisher
from rclpy.timer import Timer
from std_msgs.msg import String


class LifecyclePublisher(Node):
    def __init__(self) -> None:
        super().__init__('lifecycle_publisher')
        self._publisher: Publisher | None = None
        self._timer: Timer | None = None
        self._sequence = 0
        # 起動後に自動で configure を発行
        self._startup_timer = self.create_timer(0.5, self._trigger_configure)

    def _trigger_configure(self) -> None:
        self._startup_timer.cancel()
        self.get_logger().info('[unconfigured] Triggering configure...')
        self.trigger_configure()

    # ------------------------------------------------------------------
    # Lifecycle callbacks
    # ------------------------------------------------------------------
    def on_configure(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info(
            f'[{state.label}] -> [inactive] Configuring: creating publisher.'
        )
        self._publisher = self.create_lifecycle_publisher(
            String, 'chatter', 10
        )
        self._sequence = 0
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info(
            f'[{state.label}] -> [active] Activating: starting timer.'
        )
        self._timer = self.create_timer(1.0, self.publish_message)
        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info(
            f'[{state.label}] -> [inactive] Deactivating: stopping timer.'
        )
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        return super().on_deactivate(state)

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info(
            f'[{state.label}] -> [unconfigured] Cleaning up.'
        )
        self._publisher = None
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info(
            f'[{state.label}] -> [finalized] Shutting down.'
        )
        return TransitionCallbackReturn.SUCCESS

    # ------------------------------------------------------------------
    # Timer callback
    # ------------------------------------------------------------------
    def publish_message(self) -> None:
        if self._publisher is None or not self._publisher.is_activated:
            return
        msg = String()
        msg.data = f'Hello from lifecycle_publisher: {self._sequence}'
        self._publisher.publish(msg)
        self.get_logger().info(f'Published: {msg.data}')
        self._sequence += 1


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LifecyclePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
