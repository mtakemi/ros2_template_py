import rclpy
from rclpy.lifecycle import Node, State, TransitionCallbackReturn
from std_msgs.msg import String


class LifecycleSubscriber(Node):
    def __init__(self) -> None:
        super().__init__('lifecycle_subscriber')
        self._subscription = None
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
            f'[{state.label}] -> [inactive] Configuring: creating subscription.'
        )
        self._subscription = self.create_subscription(
            String, 'chatter', self.on_message, 10
        )
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info(
            f'[{state.label}] -> [active] Activating: ready to receive messages.'
        )
        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info(
            f'[{state.label}] -> [inactive] Deactivating.'
        )
        return super().on_deactivate(state)

    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info(
            f'[{state.label}] -> [unconfigured] Cleaning up.'
        )
        self._subscription = None
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        self.get_logger().info(
            f'[{state.label}] -> [finalized] Shutting down.'
        )
        return TransitionCallbackReturn.SUCCESS

    # ------------------------------------------------------------------
    # Subscription callback
    # ------------------------------------------------------------------
    def on_message(self, msg: String) -> None:
        self.get_logger().info(f'Received: {msg.data}')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LifecycleSubscriber()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
