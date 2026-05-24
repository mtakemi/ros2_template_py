from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

# =============================================================================
# Launch Argument vs Node Parameter — launch ファイル側の解説
# =============================================================================
#
# ■ Launch Argument（このファイルで定義）
#   - DeclareLaunchArgument() で宣言する
#   - ros2 launch コマンドで渡す: ros2 launch pkg file.py greeting:=Hi
#   - LaunchConfiguration('name') でこのファイル内から参照できる
#   - ノードコードからは直接アクセスできない
#
# ■ Node Parameter（ノード側で定義）
#   - ノード(argument_vs_parameter_demo.py)の declare_parameter() で宣言
#   - Node(parameters=[...]) に渡すことで、Argument の値を Parameter として注入できる
#     → これが Argument → Parameter の「橋渡し」
#
# ■ ファイルパスでの設定
#   - config_file Argument に YAML ファイルパスを渡すと Node(parameters=[path]) として読み込まれる
#   - デフォルトはインストール済みの config/argument_vs_parameter_demo.yaml
#   - カスタムファイルを渡す例:
#       ros2 launch ros2_template_py argument_vs_parameter_demo.launch.py \
#         config_file:=/home/user/my_config.yaml
#
# =============================================================================


def generate_launch_description() -> LaunchDescription:
    """Launch ファイルのエントリポイント."""

    # --- Launch Arguments の宣言 ---
    # ここで宣言した引数は ros2 launch コマンドから上書きできる
    # 例: ros2 launch ros2_template_py argument_vs_parameter_demo.launch.py greeting:=Hi

    config_file_arg = DeclareLaunchArgument(
        'config_file',
        # デフォルト: インストール済みの YAML ファイルを使用
        default_value=PathJoinSubstitution([
            FindPackageShare('ros2_template_py'),
            'config',
            'argument_vs_parameter_demo.yaml',
        ]),
        description=(
            '[Launch Argument] Node Parameter を読み込む YAML ファイルのパス。 '
            '例: config_file:=/path/to/custom.yaml'
        ),
    )

    greeting_arg = DeclareLaunchArgument(
        'greeting',
        default_value='Hello',
        description=(
            '[Launch Argument] 挨拶のプレフィックス。'
            'YAML ファイルの値より優先されるインライン上書き。'
        ),
    )

    target_name_arg = DeclareLaunchArgument(
        'target_name',
        default_value='World',
        description='[Launch Argument] 挨拶の宛先。',
    )

    publish_rate_arg = DeclareLaunchArgument(
        'publish_rate',
        default_value='1.0',
        description='[Launch Argument] パブリッシュ周期 [秒]。',
    )

    # --- Node の定義 ---
    # parameters リストに以下を渡している:
    #   1. YAML ファイルパス  → LaunchConfiguration('config_file') で解決
    #   2. インライン dict    → Argument の値を直接 Parameter として注入
    # ※ 同名のパラメータはリストの後ろ側が優先される
    node = Node(
        package='ros2_template_py',
        executable='argument_vs_parameter_demo',
        name='argument_vs_parameter_demo',
        output='screen',
        arguments=['--ros-args', '--log-level', 'info'],
        parameters=[
            # 1. YAML ファイルで一括設定 (Launch Argument で上書き可)
            LaunchConfiguration('config_file'),
            # 2. Launch Argument の値をインラインで Node Parameter として注入
            #    → YAML の値より後ろにあるためこちらが優先される
            {
                'greeting': LaunchConfiguration('greeting'),
                'target_name': LaunchConfiguration('target_name'),
                'publish_rate': LaunchConfiguration('publish_rate'),
            },
        ],
    )

    return LaunchDescription([
        config_file_arg,
        greeting_arg,
        target_name_arg,
        publish_rate_arg,
        node,
    ])
