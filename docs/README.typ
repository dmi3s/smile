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

#v(1em)
Realtime pipeline of three worker threads:

- _camera_ — webcam capture (`frame_ready` to UI and face worker)
- _face_ — MediaPipe FaceDetector, publishes normalized boxes
- _smile_ — MediaPipe FaceLandmarker, computes smile score `max(openness, spread)` from mouth landmarks (`13`/`14`, `61`/`291`, eyes `33`/`263`)

Each worker consumes only the latest available input via a mailbox; stale frames are dropped for low latency. UI shows emoji status: `🖖` no face / `😐` neutral / `😊` smile / `😄` big smile.