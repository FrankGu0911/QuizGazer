"""
复选框状态检查工具类
提供健壮的复选框状态处理方法，解决跨平台兼容性问题
"""

from PySide6.QtWidgets import QCheckBox
from PySide6.QtCore import Qt
from typing import Union, Any


class CheckboxStateHandler:
    """复选框状态处理工具类"""
    
    @staticmethod
    def is_checked_safe(checkbox_or_state: Union[QCheckBox, int, Any]) -> bool:
        """
        安全的复选框状态检查方法
        
        Args:
            checkbox_or_state: QCheckBox对象、状态整数值或其他状态值
            
        Returns:
            bool: 是否选中
        """
        try:
            if isinstance(checkbox_or_state, QCheckBox):
                # 直接从复选框对象获取状态（推荐方式）
                return checkbox_or_state.isChecked()
            elif isinstance(checkbox_or_state, int):
                # 处理stateChanged信号的整数参数
                return CheckboxStateHandler._is_checked_from_int_state(checkbox_or_state)
            elif hasattr(checkbox_or_state, 'value'):
                # 处理Qt.CheckState枚举
                return checkbox_or_state == Qt.CheckState.Checked
            else:
                # 其他类型，尝试转换为布尔值
                return bool(checkbox_or_state)
        except Exception as e:
            print(f"复选框状态检查失败: {e}")
            return False  # 默认返回未选中状态
    
    @staticmethod
    def _is_checked_from_int_state(state: int) -> bool:
        """
        从整数状态值判断是否选中
        
        Args:
            state: 状态整数值 (0=未选中, 1=部分选中, 2=选中)
            
        Returns:
            bool: 是否选中
        """
        try:
            # 方法1: 与Qt.CheckState.Checked的值比较
            if hasattr(Qt.CheckState, 'Checked'):
                checked_value = Qt.CheckState.Checked.value if hasattr(Qt.CheckState.Checked, 'value') else Qt.CheckState.Checked
                if state == checked_value:
                    return True
            
            # 方法2: 直接数值比较（备用）
            if state == 2:
                return True
                
            return False
        except Exception as e:
            print(f"整数状态检查失败: {e}")
            # 最后的备用方案
            return state == 2
    
    @staticmethod
    def get_checkbox_state_robust(checkbox: QCheckBox) -> tuple[bool, str]:
        """
        健壮的复选框状态获取，返回状态和调试信息
        
        Args:
            checkbox: QCheckBox对象
            
        Returns:
            tuple: (是否选中, 调试信息)
        """
        debug_info = []
        
        try:
            # 方法1: 使用isChecked()
            is_checked_method = checkbox.isChecked()
            debug_info.append(f"isChecked(): {is_checked_method}")
        except Exception as e:
            is_checked_method = None
            debug_info.append(f"isChecked() 失败: {e}")
        
        try:
            # 方法2: 使用checkState()
            check_state = checkbox.checkState()
            is_checked_state = CheckboxStateHandler._is_checked_from_int_state(check_state)
            debug_info.append(f"checkState(): {check_state} -> {is_checked_state}")
        except Exception as e:
            is_checked_state = None
            debug_info.append(f"checkState() 失败: {e}")
        
        # 确定最终结果
        if is_checked_method is not None:
            final_result = is_checked_method
            debug_info.append("使用 isChecked() 结果")
        elif is_checked_state is not None:
            final_result = is_checked_state
            debug_info.append("使用 checkState() 结果")
        else:
            final_result = False
            debug_info.append("所有方法失败，默认为 False")
        
        return final_result, "; ".join(debug_info)
    
    @staticmethod
    def setup_checkbox_connection_safe(checkbox: QCheckBox, callback_func):
        """
        安全的复选框信号连接设置
        
        Args:
            checkbox: QCheckBox对象
            callback_func: 回调函数（不接受参数）
        """
        try:
            # 推荐方式：连接到不带参数的回调函数
            checkbox.stateChanged.connect(callback_func)
        except Exception as e:
            print(f"复选框信号连接失败: {e}")
    
    @staticmethod
    def setup_checkbox_connection_with_state(checkbox: QCheckBox, callback_func):
        """
        带状态参数的复选框信号连接设置
        
        Args:
            checkbox: QCheckBox对象
            callback_func: 回调函数（接受一个state参数）
        """
        try:
            # 使用lambda包装，提供健壮的状态检查
            checkbox.stateChanged.connect(
                lambda state: callback_func(CheckboxStateHandler.is_checked_safe(state))
            )
        except Exception as e:
            print(f"复选框信号连接失败: {e}")


# 便捷函数
def is_checkbox_checked(checkbox: QCheckBox) -> bool:
    """
    便捷函数：检查复选框是否选中
    
    Args:
        checkbox: QCheckBox对象
        
    Returns:
        bool: 是否选中
    """
    return CheckboxStateHandler.is_checked_safe(checkbox)


def get_checkbox_state_debug(checkbox: QCheckBox) -> tuple[bool, str]:
    """
    便捷函数：获取复选框状态和调试信息
    
    Args:
        checkbox: QCheckBox对象
        
    Returns:
        tuple: (是否选中, 调试信息)
    """
    return CheckboxStateHandler.get_checkbox_state_robust(checkbox)


# 示例用法
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
    
    app = QApplication([])
    
    class TestWidget(QWidget):
        def __init__(self):
            super().__init__()
            layout = QVBoxLayout(self)
            
            self.checkbox = QCheckBox("测试复选框")
            self.test_button = QPushButton("测试状态")
            
            # 使用安全的信号连接
            CheckboxStateHandler.setup_checkbox_connection_safe(
                self.checkbox, self.on_checkbox_changed
            )
            
            self.test_button.clicked.connect(self.test_checkbox_state)
            
            layout.addWidget(self.checkbox)
            layout.addWidget(self.test_button)
        
        def on_checkbox_changed(self):
            """复选框状态变化处理"""
            is_checked = is_checkbox_checked(self.checkbox)
            print(f"复选框状态变化: {is_checked}")
        
        def test_checkbox_state(self):
            """测试复选框状态获取"""
            is_checked, debug_info = get_checkbox_state_debug(self.checkbox)
            print(f"当前状态: {is_checked}")
            print(f"调试信息: {debug_info}")
    
    widget = TestWidget()
    widget.show()
    
    app.exec()