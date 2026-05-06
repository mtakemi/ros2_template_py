# Copyright 2026 ros2_template_py
#
# This software is released under the MIT License.
# See the LICENSE file for details.
"""MultiThreadedExecutor で複数 Node を並列実行するサンプル。"""

from __future__ import annotations

import time

import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Int32


class ProducerWorkerNode(Node):
    """publish と重い処理を1つの Node で行う。"""

    def __init__(self) -> None:
        super().__init__('producer_worker_node')
        # heavy work は同時実行させない。publish は別グループで継続実行する。
        self._publish_group = ReentrantCallbackGroup()
        self._work_group = MutuallyExclusiveCallbackGroup()
        self._pub = self.create_publisher(Int32, 'work_items', 10)
        self._sub = self.create_subscription(
            Int32,
            'work_items',
            self._on_message,
            10,
            callback_group=self._work_group,
        )
        self._counter = 0
        self._timer = self.create_timer(
            0.5,
            self._on_timer,
            callback_group=self._publish_group,
        )

    def _on_timer(self) -> None:
        msg = Int32()
        msg.data = self._counter
        self._pub.publish(msg)
        self.get_logger().info(f'Published work item: {msg.data}')
        self._counter += 1

    def _on_message(self, msg: Int32) -> None:
        self.get_logger().info(f'Start heavy work: {msg.data}')
        # 重い処理の代替。MultiThreadedExecutor だと他ノードのコールバックが止まりにくい。
        time.sleep(2.0)
        self.get_logger().info(f'Done heavy work: {msg.data}')


class MonitorNode(Node):
    """並列動作確認用のハートビートを出す。"""

    def __init__(self) -> None:
        super().__init__('monitor_node')
        self._timer = self.create_timer(0.3, self._on_heartbeat)

    def _on_heartbeat(self) -> None:
        self.get_logger().info('Heartbeat...')


def main(args=None) -> None:
    rclpy.init(args=args)

    producer_worker = ProducerWorkerNode()
    monitor = MonitorNode()

    executor = MultiThreadedExecutor(num_threads=3)
    executor.add_node(producer_worker)
    executor.add_node(monitor)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        producer_worker.destroy_node()
        monitor.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
