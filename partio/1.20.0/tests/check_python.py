from pathlib import Path

import partio


particles = partio.create()
position = particles.addAttribute("position", partio.VECTOR, 3)
index = particles.addParticle()
particles.set(position, index, (1.0, 2.0, 3.0))

path = Path("partio_python.bgeo")
partio.write(str(path), particles)

read = partio.read(str(path), False)
assert read.numParticles() == 1
read_position = read.attributeInfo("position")
assert tuple(read.get(read_position, 0)) == (1.0, 2.0, 3.0)
