import libcst as cst
from sparkling_water.core.code_editor import CodeEditor, EditIntent, EditOperation
import asyncio

async def test():
    editor = CodeEditor()
    code = """def hello():
    print("old")
"""
    with open("temp_test.py", "w") as f:
        f.write(code)

    intent = EditIntent(
        operation=EditOperation.EDIT,
        target_file="temp_test.py",
        target_function="hello",
        new_content="print('new1')\nprint('new2')"
    )

    result = await editor.edit_code(intent)
    if result.success:
        print("Success!")
        print(result.modified_content)
    else:
        print(f"Failed: {result.error}")

asyncio.run(test())
