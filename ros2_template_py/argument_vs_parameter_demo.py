import rclpy
from rclpy.node import Node
from std_msgs.msg import String

# =============================================================================
# Argument vs Parameter — 概念の違い
# =============================================================================
#
# ■ Launch Argument（起動引数）
#   - launch ファイル内で DeclareLaunchArgument() により定義する
#   - ros2 launch コマンドへ渡す値: ros2 launch pkg file.py greeting:=Hi
#   - LaunchConfiguration('name') で launch ファイル内からのみ参照できる
#   - ノードのコード（Python）からは直接アクセスできない
#   - 用途: launch ファイルを柔軟に制御する（条件分岐・ノード名変更など）
#
# ■ Node Parameter（ノードパラメータ）
#   - ノード内で declare_parameter() により定義する
#   - ノードコードから self.get_parameter('name').value で取得できる
#   - 設定方法は3通り:
#       1. CLI:       ros2 run pkg node --ros-args -p greeting:=Hi
#       2. YAML:      ros2 run pkg node --ros-args --params-file config.yaml
#       3. launch:    Node(parameters=[{'greeting': 'Hi'}])
#   - 実行中に変更可能: ros2 param set /node_name greeting Hi
#   - 一覧確認:        ros2 param list /node_name
#
# ■ Launch Argument → Parameter の橋渡し
#   launch ファイルが Argument の値を Parameter として node に注入することで
#   「launchコマンドの引数が最終的にノードに届く」仕組みになっている。
#
# =============================================================================


class ArgumentVsParameterDemo(Node):
    """Argument と Parameter の違いを示すデモノード."""

    def __init__(self) -> None:
        """ノードの初期化とパラメータ宣言."""
        super().__init__('argument_vs_parameter_demo')

        # --- Node Parameter を宣言 ---
        # declare_parameter(名前, デフォルト値)
        # デフォルト値は YAML ファイルや CLI で上書きできる
        self.declare_parameter('greeting', 'Hello')
        self.declare_parameter('target_name', 'World')
        self.declare_parameter('publish_rate', 1.0)
        self.declare_parameter('config_file_path', '')

        # パラメータ値を取得
        greeting = self.get_parameter('greeting').get_parameter_value().string_value
        target = self.get_parameter('target_name').get_parameter_value().string_value
        rate = self.get_parameter('publish_rate').get_parameter_value().double_value
        config_path = self.get_parameter('config_file_path').get_parameter_value().string_value

        # 起動時に現在のパラメータ値をログ出力
        self.get_logger().info('=== Node Parameter の現在値 ===')
        self.get_logger().info(f'  greeting         : {greeting}')
        self.get_logger().info(f'  target_name      : {target}')
        self.get_logger().info(f'  publish_rate     : {rate}')
        self.get_logger().info(f'  config_file_path : {config_path if config_path else "(未指定)"}')
        self.get_logger().info('')
        self.get_logger().info('--- 設定方法ヒント ---')
        self.get_logger().info('  CLI:    ros2 run ros2_template_py argument_vs_parameter_demo')
        self.get_logger().info('            --ros-args -p greeting:=Hi -p target_name:=ROS2')
        self.get_logger().info('  YAML:   ros2 run ros2_template_py argument_vs_parameter_demo')
        self.get_logger().info('            --ros-args --params-file config/argument_vs_parameter_demo.yaml')
        self.get_logger().info('  launch: ros2 launch ros2_template_py argument_vs_parameter_demo.launch.py')
        self.get_logger().info('            greeting:=Hi config_file:=/path/to/config.yaml')
        self.get_logger().info('  実行中変更: ros2 param set /argument_vs_parameter_demo greeting Bye')

        self.publisher_ = self.create_publisher(String, 'demo_topic', 10)
        self.timer = self.create_timer(rate, self.on_timer)

    def on_timer(self) -> None:
        """タイマーコールバック: パラメータ値を使ってメッセージをパブリッシュ."""
        # get_parameter は毎回呼ぶことで実行中のパラメータ変更(ros2 param set)を反映できる
        greeting = self.get_parameter('greeting').get_parameter_value().string_value
        target = self.get_parameter('target_name').get_parameter_value().string_value
        msg = String()
        msg.data = f'{greeting}, {target}!'
        self.publisher_.publish(msg)
        self.get_logger().info(f'Published: "{msg.data}"')


def main(args=None) -> None:
    """エントリポイント."""
    rclpy.init(args=args)
    node = ArgumentVsParameterDemo()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
