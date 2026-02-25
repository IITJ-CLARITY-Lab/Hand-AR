from panda3d.core import loadPrcFileData
loadPrcFileData('', 'win-size 1280 720')

from ursina import *

app = Ursina(borderless=False)

window.color = color.black
window.fps_counter.enabled = True

Sky(color=color.azure)


test_cube = Entity(
    model='cube',
    scale=10,
    color=color.red,
    position=(0,5,20)
)


ground = Entity(
    model='plane',
    scale=(100,1,100),
    color=color.green,
    collider='box'
)


DirectionalLight()
AmbientLight(color=color.rgba(150,150,150,0.5))


camera.position = (0,10,-30)
camera.rotation = (0,0,0)
mouse.locked = True


speed = 20
sensitivity = 100

def update():
    camera.rotation_y += mouse.velocity[0] * sensitivity
    camera.rotation_x -= mouse.velocity[1] * sensitivity
    camera.rotation_x = clamp(camera.rotation_x, -89, 89)

    direction = Vec3(
        held_keys['d'] - held_keys['a'],
        held_keys['e'] - held_keys['q'],
        held_keys['w'] - held_keys['s']
    )

    movement = (
        camera.forward * direction.z +
        camera.right * direction.x +
        Vec3(0,1,0) * direction.y
    )

    camera.position += movement * time.dt * speed


app.run()