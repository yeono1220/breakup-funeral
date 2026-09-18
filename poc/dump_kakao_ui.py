"""PoC 0: 카톡 PC 창의 UIA 트리를 덤프해서 자동화 가능한 요소가 뭐가 있는지 확인."""
import sys
from pywinauto import Desktop


def dump(elem, depth=0, max_depth=6, max_children=60):
    ei = elem.element_info
    name = (ei.name or "")[:60].replace("\n", "\\n")
    print(f"{'  ' * depth}[{ei.control_type}] name={name!r} class={ei.class_name!r} "
          f"auto_id={ei.automation_id!r} rect={ei.rectangle}")
    if depth >= max_depth:
        return
    try:
        children = elem.children()
    except Exception as e:  # noqa: BLE001
        print(f"{'  ' * (depth + 1)}<children error: {e}>")
        return
    for c in children[:max_children]:
        dump(c, depth + 1, max_depth, max_children)
    if len(children) > max_children:
        print(f"{'  ' * (depth + 1)}... +{len(children) - max_children} more")


def main():
    desk = Desktop(backend="uia")
    wins = [w for w in desk.windows()
            if "EVA_" in (w.element_info.class_name or "") or "카카오톡" in w.window_text()]
    print(f"== 카톡 관련 최상위 창 {len(wins)}개")
    for w in wins:
        ei = w.element_info
        print(f"  title={w.window_text()!r} class={ei.class_name!r} visible={w.is_visible()} rect={ei.rectangle}")

    if not wins:
        print("카톡 창을 못 찾음. 트레이에서 열어서 메인 창을 띄운 뒤 다시 실행.")
        sys.exit(1)

    for w in wins:
        print(f"\n== 덤프: {w.window_text()!r} class={w.element_info.class_name!r}")
        dump(w)


if __name__ == "__main__":
    main()
