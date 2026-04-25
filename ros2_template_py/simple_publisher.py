import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SimplePublisher(Node):
    def __init__(self) -> None:
        super().__init__('simple_publisher')
        self.publisher_ = self.create_publisher(String, 'chatter', 10)
        self.timer = self.create_timer(1.0, self.publish_message)
        self.sequence = 0

    def publish_message(self) -> None:
        msg = String()
        msg.data = f'Hello, ROS2! [{self.sequence}]'
        self.publisher_.publish(msg)
        self.get_logger().info(f'Published: {msg.data}')
        self.sequence += 1


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SimplePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
