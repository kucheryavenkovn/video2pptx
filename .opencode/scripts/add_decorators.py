import re
from pathlib import Path

path = Path('src/video2pptx/gui/main_window.py')
text = path.read_text(encoding='utf-8')

# 1. Add mcp_action import
text = text.replace(
    'from video2pptx.project_model import ProjectModel',
    'from video2pptx.project_model import ProjectModel\nfrom video2pptx.debug.action_registry import mcp_action'
)

# 2. Add _confirm method
confirm = '''
    def _confirm(self, title: str, text: str) -> bool:
        if self._mcp_active:
            return True
        return QMessageBox.question(self, title, text,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes
'''
text = text.replace(
    '\n    def _connect_menu_signals(self) -> None:',
    confirm + '\n\n    def _connect_menu_signals(self) -> None:'
)

# 3. Wrap mcp_process_queue
text = text.replace(
    'lambda: mcp_process_queue(self._model)',
    'lambda: [setattr(self, "_mcp_active", True), mcp_process_queue(self._model), setattr(self, "_mcp_active", False)]'
)

# 4. @mcp_action decorators
decorators = {
    '    def _on_detect(self) -> None:': "    @mcp_action(name='detect', desc='Run full slide detection')\n    def _on_detect(self) -> None:",
    '    def _on_quick_detect(self) -> None:': "    @mcp_action(name='detect_quick', desc='Run quick detection')\n    def _on_quick_detect(self) -> None:",
    '    def _on_export_md(self) -> None:': "    @mcp_action(name='export_md', desc='Export to Markdown')\n    def _on_export_md(self) -> None:",
    '    def _on_export_pptx(self) -> None:': "    @mcp_action(name='export_pptx', desc='Export to PPTX')\n    def _on_export_pptx(self) -> None:",
    '    def _on_process_notes(self) -> None:': "    @mcp_action(name='notes', desc='Process speaker notes')\n    def _on_process_notes(self) -> None:",
    '    def _on_seek_to_marker(self, ts: float) -> None:': "    @mcp_action(name='seek', desc='Seek video to position')\n    def _on_seek_to_marker(self, ts: float) -> None:",
    '    def _on_open_subtitle_editor(self, slide_index: int) -> None:': "    @mcp_action(name='edit_subtitles', desc='Open subtitle editor')\n    def _on_open_subtitle_editor(self, slide_index: int) -> None:",
    '    def _on_add_manual_slide(self, ts: float) -> None:': "    @mcp_action(name='slide_add_ui', desc='Add manual slide at timestamp')\n    def _on_add_manual_slide(self, ts: float) -> None:",
    '    def _on_set_slide_frame(self, slide_index: int) -> None:': "    @mcp_action(name='slide_set_frame', desc='Capture frame as slide image')\n    def _on_set_slide_frame(self, slide_index: int) -> None:",
    '    def _on_clear_slide_image(self, slide_index: int) -> None:': "    @mcp_action(name='slide_clear_image', desc='Clear slide image')\n    def _on_clear_slide_image(self, slide_index: int) -> None:",
    '    def _on_delete_slide(self, slide_index: int) -> None:': "    @mcp_action(name='slide_delete_ui', desc='Delete slide by index')\n    def _on_delete_slide(self, slide_index: int) -> None:",
    '    def _on_open_marker_panel(self) -> None:': "    @mcp_action(name='marker_panel', desc='Open marker panel dialog')\n    def _on_open_marker_panel(self) -> None:",
    '    def _on_add_marker_at_position(self) -> None:': "    @mcp_action(name='add_marker', desc='Add marker at current position')\n    def _on_add_marker_at_position(self) -> None:",
    '    def _on_slide_moved(self, index: int, new_start: float, new_end: float) -> None:': "    @mcp_action(name='slide_moved', desc='Move slide to new start/end')\n    def _on_slide_moved(self, index: int, new_start: float, new_end: float) -> None:",
    '    def _on_slide_resized(self, index: int, new_start: float, new_end: float) -> None:': "    @mcp_action(name='slide_resize', desc='Resize slide interval')\n    def _on_slide_resized(self, index: int, new_start: float, new_end: float) -> None:",
    '    def _on_open_timeline_image(self, path: str, slide_index: int = 0) -> None:': "    @mcp_action(name='slide_show_image', desc='Show slide image overlay in video player')\n    def _on_open_timeline_image(self, path: str, slide_index: int = 0) -> None:",
}

count = 0
for old, new in decorators.items():
    if old in text:
        text = text.replace(old, new, 1)
        count += 1
        print(f'  + {old.split("(")[0].strip().replace("def ", "")}')

path.write_text(text, encoding='utf-8')
print(f'Decorators applied: {count}')
print(f'Lines: {len(text.splitlines())}')
