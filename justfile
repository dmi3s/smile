UI_DIR := "src/smile/ui"
GEN_DIR := "src/smile/ui/generated"
RES_DIR := "src/smile/resources"

bootstrap: sync generate

sync:
    uv sync

gen-ui:
    mkdir -p {{ GEN_DIR }}

    uv run pyside6-uic \
        {{ UI_DIR }}/main_window.ui \
        -o {{ GEN_DIR }}/ui_main_window.py

    sed -i \
        's/^import resources_rc$/from . import resources_rc/' \
        src/smile/ui/generated/ui_main_window.py

gen-resources:
    uv run pyside6-rcc \
        {{ RES_DIR }}/resources.qrc \
        -o {{ GEN_DIR }}/resources_rc.py

generate: gen-ui gen-resources

run:
    uv run smile

clean:
    rm *.log
    uv clean
#    uv venv --clear
