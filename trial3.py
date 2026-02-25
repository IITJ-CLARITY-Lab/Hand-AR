from panda3d.core import loadPrcFileData
loadPrcFileData('', 'win-size 1280 720')

from ursina import *

app = Ursina(borderless=False)

window.fps_counter.enabled = True

Sky()


terrain = Entity(
    model='low_poly_mountains.glb',   # put your file name here
    scale=5,                # adjust scale if needed
)

DirectionalLight()
AmbientLight(color=color.rgba(150,150,150,0.4))


camera.position = (0, 50, -150)
camera.far = 50000
mouse.locked = True

speed = 60
sensitivity = 200

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