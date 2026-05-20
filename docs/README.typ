#set text(font: "DejaVu Sans")

= Smile project
#grid(
  columns: (10%, 75%),
  gutter: 1em,
  align: bottom,
  [
    #image("images/smile-lol.png", width: 40pt)
  ],
  [
    _Realtime face detection playground built with Python, Qt and MediaPipe._
  ],
)
#v(1em)
The project captures webcam frames, runs face detection in a separate worker thread and renders detection overlays in a PySide6 UI.
