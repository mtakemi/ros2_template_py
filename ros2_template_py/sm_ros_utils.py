# Copyright 2026 ros2_template_py
#
# This software is released under the MIT License.
# See the LICENSE file for details.
"""transitions × ROS2 Parameter / Service Client 統合ユーティリティ。

trigger の外部公開は ``fire_trigger`` パラメータ 1 本で行う。
trigger 数が増えてもインターフェースは変わらない。

使い方 (最小例)::

    from std_srvs.srv import SetBool
    from ros2_template_py.sm_ros_utils import SmRosNode

    class MyNode(SmRosNode):
        _sm_states = ['IDLE', 'CHECKING', 'WORKING', 'DONE']
        _sm_transitions = [
            {'trigger': 'start',      'source': 'IDLE',     'dest': 'CHECKING'},
            {'trigger': 'check_ok',   'source': 'CHECKING', 'dest': 'WORKING'},
            {'trigger': 'check_fail', 'source': 'CHECKING', 'dest': 'IDLE'},
            {'trigger': 'finish',     'source': 'WORKING',  'dest': 'DONE'},
            {'trigger': 'reset',      'source': '*',        'dest': 'IDLE'},
        ]
        _sm_initial = 'IDLE'

        def on_enter_CHECKING(self) -> None:
            req = SetBool.Request()
            req.data = True
            self.call_service_on_enter(
                SetBool, '/robot/check',
                req,
                on_success='check_ok',
                on_failure='check_fail',
            )

trigger の発火::

    ros2 param set /my_node fire_trigger start
    ros2 param set /my_node fire_trigger reset

現在の状態の確認::

    ros2 topic echo /state_output
    ros2 param get /my_node current_state
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Type

from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import String
from transitions import Machine


# ---------------------------------------------------------------------------
# Public dataclass: サービス呼び出し設定の宣言的定義用
# ---------------------------------------------------------------------------

@dataclass
class ServiceCallConfig:
    """on_enter_<STATE> でのサービス呼び出し設定を宣言的に記述するデータクラス。

    例::

        CHECKING_SERVICE = ServiceCallConfig(
            srv_type=SetBool,
            srv_name='/robot/check',
            on_success='check_ok',
            on_failure='check_fail',
        )

    SmRosNode.call_service_on_enter() の引数にそのまま展開して使う::

        self.call_service_on_enter(
            **CHECKING_SERVICE.as_kwargs(request=req)
        )
    """

    srv_type: Any
    srv_name: str
    on_success: str | None = None
    on_failure: str | None = None
    extra_kwargs: dict = field(default_factory=dict)

    def as_kwargs(self, request: Any) -> dict:
        """call_service_on_enter に渡せる辞書を返す。"""
        return {
            'srv_type': self.srv_type,
            'srv_name': self.srv_name,
            'request': request,
            'on_success': self.on_success,
            'on_failure': self.on_failure,
            **self.extra_kwargs,
        }


# ---------------------------------------------------------------------------
# Core: SmRosNode
# ---------------------------------------------------------------------------

class SmRosNode(Node):
    """transitions.Machine + rclpy.Node を統合したベースクラス。

    サブクラスでクラス変数を宣言するだけで以下が自動セットアップされる:

    - ``fire_trigger`` パラメータ (string) — trigger 名を set するだけで発火
    - ``current_state`` パラメータ (string, read-only) — 現在の状態を外部から確認可能
    - 状態変化を ``state_output`` (std_msgs/String) トピックへ自動パブリッシュ

    trigger の発火::

        ros2 param set /my_node fire_trigger start
        ros2 param set /my_node fire_trigger reset

    状態の確認::

        ros2 param get /my_node current_state
        ros2 topic echo /state_output

    サービス呼び出し連携:

    - :meth:`call_service_on_enter` を ``on_enter_<STATE>`` から呼ぶと、
      レスポンスの ``success`` フィールドに応じて次の trigger を自動発火する。
    """

    # ---- サブクラスでオーバーライドする ----
    _sm_states: list[str] = []
    _sm_transitions: list[dict] = []
    _sm_initial: str = ''
    # ----------------------------------------

    def __init__(self, node_name: str) -> None:
        super().__init__(node_name)

        if not self._sm_initial:
            raise ValueError(
                f'{type(self).__name__}: _sm_initial が未設定です。'
            )

        self._machine = Machine(
            model=self,
            states=self._sm_states,
            transitions=self._sm_transitions,
            initial=self._sm_initial,
            ignore_invalid_triggers=True,
            after_state_change='_on_state_changed',
        )
        self._state_pub = self.create_publisher(String, 'state_output', 10)
        self._service_callers: dict[str, _AsyncServiceCaller] = {}

        # fire_trigger: ros2 param set で trigger 名を渡すと発火
        self.declare_parameter(
            'fire_trigger',
            '',
            ParameterDescriptor(description='Fire a state machine trigger by name.'),
        )
        # current_state: 現在の状態を外部から読める (read-only 運用)
        self.declare_parameter(
            'current_state',
            self._sm_initial,
            ParameterDescriptor(
                description='Current state (read-only; do not set directly).',
                read_only=False,
            ),
        )
        self.add_on_set_parameters_callback(self._on_set_parameters)
        self.get_logger().info(
            f'{node_name} started. state={self.state}'
        )

    # ------------------------------------------------------------------
    # Parameter callback
    # ------------------------------------------------------------------

    def _on_set_parameters(
        self, params: list[Parameter]
    ) -> SetParametersResult:
        for param in params:
            if param.name == 'fire_trigger':
                result = self._handle_fire_trigger(param.value)
                if not result.successful:
                    return result
        return SetParametersResult(successful=True)

    def _handle_fire_trigger(self, trigger_name: str) -> SetParametersResult:
        """fire_trigger パラメータを受けて trigger を発火する。"""
        if not trigger_name:
            return SetParametersResult(successful=True)

        known = {t['trigger'] for t in self._sm_transitions}
        if trigger_name not in known:
            reason = (
                f'Unknown trigger: "{trigger_name}". '
                f'Known: {sorted(known)}'
            )
            self.get_logger().error(reason)
            return SetParametersResult(successful=False, reason=reason)

        prev = self.state
        getattr(self, trigger_name)()
        if self.state != prev:
            self.get_logger().info(
                f'fire_trigger "{trigger_name}": {prev} -> {self.state}'
            )
            return SetParametersResult(successful=True)
        reason = (
            f'Trigger "{trigger_name}" is not valid '
            f'in current state "{prev}".'
        )
        self.get_logger().error(reason)
        return SetParametersResult(successful=False, reason=reason)

    # ------------------------------------------------------------------
    # State change hook
    # ------------------------------------------------------------------

    def _on_state_changed(self) -> None:
        """状態変化時に state_output パブリッシュ・current_state 更新（オーバーライド可）。"""
        msg = String()
        msg.data = self.state
        self._state_pub.publish(msg)
        self.set_parameters([Parameter('current_state', value=self.state)])
        self.get_logger().info(f'State -> {self.state}')

    # ------------------------------------------------------------------
    # Service client helper
    # ------------------------------------------------------------------

    def call_service_on_enter(
        self,
        srv_type: Type,
        srv_name: str,
        request: Any,
        *,
        on_success: str | None = None,
        on_failure: str | None = None,
    ) -> None:
        """ステート entry から非同期でサービスを呼び出し、結果に応じて trigger を発火する。

        Parameters
        ----------
        srv_type:
            サービス型 (例: ``std_srvs.srv.SetBool``)
        srv_name:
            サービス名 (例: ``'/robot/check'``)
        request:
            サービスリクエストオブジェクト
        on_success:
            ``response.success == True`` のとき発火する trigger 名
        on_failure:
            ``response.success == False`` のとき発火する trigger 名
            (``success`` フィールドを持たないサービスでは常に on_success が使われる)
        """
        if srv_name not in self._service_callers:
            self._service_callers[srv_name] = _AsyncServiceCaller(
                self, srv_type, srv_name
            )
        caller = self._service_callers[srv_name]

        def _done(response: Any) -> None:
            success = getattr(response, 'success', True)
            trigger_name = on_success if success else on_failure
            if trigger_name:
                self.get_logger().info(
                    f'Service "{srv_name}" {"OK" if success else "NG"}'
                    f' -> trigger "{trigger_name}"'
                )
                getattr(self, trigger_name)()

        caller.call(request, callback=_done)

    def call_service_config(
        self,
        config: ServiceCallConfig,
        request: Any,
    ) -> None:
        """ServiceCallConfig を使って call_service_on_enter を呼ぶ糖衣構文。"""
        self.call_service_on_enter(**config.as_kwargs(request))


# ---------------------------------------------------------------------------
# Internal: 非同期 Service Client ラッパー
# ---------------------------------------------------------------------------

class _AsyncServiceCaller:
    """非同期 Service Client の薄いラッパー（SmRosNode 内部用）。

    初回呼び出し時にサービスの可用性をチェックし、
    利用不可の場合は警告ログを出してスキップする。
    """

    def __init__(
        self, node: Node, srv_type: Type, srv_name: str
    ) -> None:
        self._node = node
        self._client = node.create_client(srv_type, srv_name)

    def call(
        self,
        request: Any,
        callback: Callable[[Any], None],
    ) -> None:
        """非同期でサービスを呼び出す。レスポンス受信後に callback を呼ぶ。"""
        if not self._client.service_is_ready():
            self._node.get_logger().warn(
                f'Service "{self._client.srv_name}" not ready. Skipping.'
            )
            return
        future = self._client.call_async(request)
        future.add_done_callback(
            lambda f: callback(f.result())
            if f.exception() is None
            else self._node.get_logger().error(
                f'Service call failed: {f.exception()}'
            )
        )
