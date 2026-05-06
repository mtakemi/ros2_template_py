# Copyright 2026 ros2_template_py
#
# This software is released under the MIT License.
# See the LICENSE file for details.
"""SmRosNode の使用例 — サービス呼び出しで状態遷移するロボットタスクノード。

状態遷移図::

    IDLE ──start──> CHECKING ──check_ok──> WORKING ──finish──> DONE
                        │                                         │
                    check_fail                                  reset
                        │                                         │
                        └──────────────────────────────────> IDLE <──┘

CHECKING に入ると /robot/check_status (std_srvs/SetBool) を自動呼び出し:
    - success=True  -> check_ok  トリガ発火 (WORKING へ)
    - success=False -> check_fail トリガ発火 (IDLE へ)

コマンドで試す::

    ros2 param set /sm_example_node fire_trigger start
    ros2 param set /sm_example_node fire_trigger reset
    ros2 param get /sm_example_node current_state
    ros2 topic echo /state_output
"""

import rclpy
from std_srvs.srv import SetBool

from ros2_template_py.sm_ros_utils import ServiceCallConfig, SmRosNode


# サービス呼び出し設定をクラス外で宣言（再利用・テスト容易性向上）
_CHECK_SERVICE = ServiceCallConfig(
    srv_type=SetBool,
    srv_name='/robot/check_status',
    on_success='check_ok',
    on_failure='check_fail',
)


class SmExampleNode(SmRosNode):
    """SmRosNode を継承したサービス連携ステートマシンの最小例。"""

    _sm_states = ['IDLE', 'CHECKING', 'WORKING', 'DONE']
    _sm_transitions = [
        {'trigger': 'start',      'source': 'IDLE',     'dest': 'CHECKING'},
        {'trigger': 'check_ok',   'source': 'CHECKING', 'dest': 'WORKING'},
        {'trigger': 'check_fail', 'source': 'CHECKING', 'dest': 'IDLE'},
        {'trigger': 'finish',     'source': 'WORKING',  'dest': 'DONE'},
        {'trigger': 'reset',      'source': '*',        'dest': 'IDLE'},
    ]
    _sm_initial = 'IDLE'

    def __init__(self) -> None:
        super().__init__('sm_example_node')

    # ------------------------------------------------------------------
    # on_enter_<STATE> コールバック
    # ------------------------------------------------------------------

    def on_enter_IDLE(self) -> None:
        self.get_logger().info(
            '[IDLE] Ready. Use "ros2 param set /sm_example_node fire_trigger start".'
        )

    def on_enter_CHECKING(self) -> None:
        """CHECKING 進入時に /robot/check_status サービスを非同期呼び出し。"""
        self.get_logger().info('[CHECKING] Calling /robot/check_status ...')
        req = SetBool.Request()
        req.data = True
        # ServiceCallConfig を使う書き方
        self.call_service_config(_CHECK_SERVICE, req)

        # 直接書く場合は以下と等価:
        # self.call_service_on_enter(
        #     SetBool, '/robot/check_status', req,
        #     on_success='check_ok',
        #     on_failure='check_fail',
        # )

    def on_enter_WORKING(self) -> None:
        self.get_logger().info(
            '[WORKING] Task running. Use "ros2 param set /sm_example_node fire_trigger finish".'
        )

    def on_enter_DONE(self) -> None:
        self.get_logger().info(
            '[DONE] All done. Use "ros2 param set /sm_example_node fire_trigger reset".'
        )


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SmExampleNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
