from typing import List, Dict

class MacroStep:
    """表示宏任务中的一个步骤"""

    def __init__(self, name: str, file_path: str, repeat:int = 1, delay: float = 0.0):
        """
        初始化宏步骤

        Args:
            name (str): 步骤名称
            file_path (str): 录制文件路径
            repeat (int): 重复次数
            delay (float): 执行后延迟(秒)
        """
        self.name = name
        self.file_path = file_path
        self.repeat = repeat
        self.delay = delay
        self.enabled = True

    def to_dict(self) -> Dict:
        """转换为字典以便序列化"""
        return {
            "name": self.name,
            "file_path": self.file_path,
            "repeat": self.repeat,
            "delay": self.delay,
            "enabled": self.enabled
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'MacroStep':
        """从字典创建实例"""
        step = cls(
            name=data.get("name", "Unnamed Step"),
            file_path=data["file_path"],
            repeat=data.get("repeat", 1),
            delay=data.get("delay", 0.0)
        )
        step.enabled = data.get("enabled", True)
        return step


class MacroTask:
    """表示一个完整的宏任务序列"""

    def __init__(self, name: str = "New Task"):
        """
        初始化宏任务

        Args:
            name (str): 任务名称
        """
        self.name = name
        self.steps: List[MacroStep] = []
        self.loop_count = 1  # 循环次数，0表示无限循环
        self.loop_delay = 0.0  # 每次循环之间的延迟
        self.current_step = 0
        self.current_loop = 0
        self.is_running = False
        self.should_stop = False

    def add_step(self, step: MacroStep):
        """添加步骤到任务"""
        self.steps.append(step)

    def insert_step(self, index: int, step: MacroStep):
        """在指定位置插入步骤"""
        self.steps.insert(index, step)

    def remove_step(self, index: int):
        """移除指定位置的步骤"""
        if 0 <= index < len(self.steps):
            del self.steps[index]

    def move_step_up(self, index: int):
        """将步骤上移"""
        if index > 0:
            self.steps[index], self.steps[index - 1] = self.steps[index - 1], self.steps[index]

    def move_step_down(self, index: int):
        """将步骤下移"""
        if index < len(self.steps) - 1:
            self.steps[index], self.steps[index + 1] = self.steps[index + 1], self.steps[index]

    def to_dict(self) -> Dict:
        """转换为字典以便序列化"""
        return {
            "name": self.name,
            "loop_count": self.loop_count,
            "loop_delay": self.loop_delay,
            "steps": [step.to_dict() for step in self.steps]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'MacroTask':
        """从字典创建实例"""
        task = cls(name=data.get("name", "Unnamed Task"))
        task.loop_count = data.get("loop_count", 1)
        task.loop_delay = data.get("loop_delay", 0.0)

        for step_data in data.get("steps", []):
            task.add_step(MacroStep.from_dict(step_data))

        return task