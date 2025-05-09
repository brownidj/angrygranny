import py5

def setup():
    py5.size(500, 400)
    py5.background(255)
    py5.fill(0)
    py5.text_size(24)
    py5.text_align(py5.CENTER, py5.CENTER)
    py5.text('Hello, Angry Granny!', py5.width / 2, py5.height / 2)

def draw():
    py5.fill(py5.random(255), py5.random(255), py5.random(255))
    py5.ellipse(py5.mouse_x, py5.mouse_y, 30, 30)

py5.run_sketch()