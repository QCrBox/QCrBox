import * as THREE from 'three';

import { TrackballControls } from 'three/addons/controls/TrackballControls.js';

var json_string;

fetch('./structure.json')
  .then(res => res.json())
  .then(data => renderJSON(data));


function renderJSON(structure_obj) {

    //////////////////////////////////////////////////////////////////////////////////
    //		Init
    //////////////////////////////////////////////////////////////////////////////////

    // init renderer
    var renderer	= new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        precision: 'mediump',
    });
    renderer.setClearColor(new THREE.Color('lightgrey'), 0)
    renderer.setSize( window.innerWidth, window.innerHeight );
    renderer.domElement.style.position = 'absolute'
    renderer.domElement.style.top = '0px'
    renderer.domElement.style.left = '0px'
    document.body.appendChild( renderer.domElement );

    // array of functions for the rendering loop
    var onRenderFcts= [];

    // init scene and camera
    var scene	= new THREE.Scene();

    //////////////////////////////////////////////////////////////////////////////////
    //		Initialize a basic camera
    //////////////////////////////////////////////////////////////////////////////////

    // Create a camera
    // const camera = new THREE.OrthographicCamera( window.innerWidth / - 2, window.innerWidth / 2, window.innerHeight / 2, window.innerHeight / - 2, 1, 1000 );
    const camera = new THREE.PerspectiveCamera( 50, window.innerWidth / window.innerHeight, 0.1, 1000 );
    
    scene.add(camera);

    const controls = new TrackballControls( camera, renderer.domElement );

    const camera_pos0 = structure_obj.default.camera_position0;
    camera.position.set( camera_pos0[0], camera_pos0[1], camera_pos0[2] );
    camera.lookAt(0, 0, 0);

    controls.update();
    //camera.rotateOnAxis(direction, -structure_obj.camera.rotation0); 


    const hemisphere_light = new THREE.HemisphereLight( 0xffffff, 0x080808, 1 );
    camera.add(hemisphere_light);

    const sphere_geom = new THREE.SphereGeometry(1, 36, 18);
    //const marker_geom = new THREE.TorusGeometry(0.94, 0.1);
    const marker_geom = new THREE.CylinderGeometry(1.01, 1.01, 0.2, 36, 1, true);

    const bond_mat = new THREE.MeshPhysicalMaterial({color: "#444444"})

    const bond_geom = new THREE.CylinderGeometry(0.04, 0.04, 1.0, 36, 1);

    const adp_scale = 1.5382;

    var materials = {}

    for (let colour_index in structure_obj.colours){
        var colour = structure_obj.colours[colour_index];
        materials[colour] = new THREE.MeshPhysicalMaterial({color: colour});
    }

    const m_ring1 = new THREE.Matrix4();
    m_ring1.set(
        1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, -1.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 1.0
    );

    const m_ring2 = new THREE.Matrix4();
    m_ring2.set(
        0.0, -1.0, 0.0, 0.0,
        1.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0
    );

    const ring_add = 0.006;


    var structureRoot = new THREE.Group;
    scene.add(structureRoot);

    for (let atom_index in structure_obj.atoms) {
        var atom_obj = structure_obj.atoms[atom_index];
        // console.log(atom_obj);
        var mat = materials[atom_obj.atom_colour];
        var ellip_mesh = new THREE.Mesh(sphere_geom, mat);
        if (atom_obj.adp_display_type == 'Uani') {
            var ani_atom_group = new THREE.Group;
            ani_atom_group.add(ellip_mesh);

            var ring_mesh = new THREE.Mesh(marker_geom, materials[atom_obj.ring_colour]);
            ani_atom_group.add(ring_mesh);

            var ring_mesh = new THREE.Mesh(marker_geom, materials[atom_obj.ring_colour]);
            ring_mesh.applyMatrix4(m_ring1);
            ani_atom_group.add(ring_mesh);

            var ring_mesh = new THREE.Mesh(marker_geom, materials[atom_obj.ring_colour]);
            ring_mesh.applyMatrix4(m_ring2);
            ani_atom_group.add(ring_mesh);

            var m = new THREE.Matrix4();
            m.set(
                atom_obj.ellipsoid_rotation[0],
                atom_obj.ellipsoid_rotation[1],
                atom_obj.ellipsoid_rotation[2],
                0.0,
                atom_obj.ellipsoid_rotation[3],
                atom_obj.ellipsoid_rotation[4],
                atom_obj.ellipsoid_rotation[5],
                0.0,
                atom_obj.ellipsoid_rotation[6],
                atom_obj.ellipsoid_rotation[7],
                atom_obj.ellipsoid_rotation[8],
                0.0, 
                0.0, 0.0, 0.0, 1.0
            );

            m.transpose();

            ani_atom_group.scale.x = adp_scale;
            ani_atom_group.scale.y = adp_scale;
            ani_atom_group.scale.z = adp_scale;

            ani_atom_group.applyMatrix4(m);
            ani_atom_group.position.x = atom_obj.Cartn_xyz[0];
            ani_atom_group.position.y = atom_obj.Cartn_xyz[1];
            ani_atom_group.position.z = atom_obj.Cartn_xyz[2];

            structureRoot.add(ani_atom_group);
        } else if (atom_obj.adp_display_type == 'constant') {
            ellip_mesh.scale.x = atom_obj.size;
            ellip_mesh.scale.y = atom_obj.size;
            ellip_mesh.scale.z = atom_obj.size;
            ellip_mesh.position.x = atom_obj.Cartn_xyz[0];
            ellip_mesh.position.y = atom_obj.Cartn_xyz[1];
            ellip_mesh.position.z = atom_obj.Cartn_xyz[2];
            structureRoot.add(ellip_mesh);
        }
    }

    for (let bond_index in structure_obj.bonds){
        var bond_obj = structure_obj.bonds[bond_index];
        var bond_mesh = new THREE.Mesh(bond_geom, bond_mat);
        bond_mesh.scale.y = bond_obj.length;
        var m = new THREE.Matrix4();
        m.set(
            bond_obj.rotation[0],
            bond_obj.rotation[1],
            bond_obj.rotation[2],
            0.0,
            bond_obj.rotation[3],
            bond_obj.rotation[4],
            bond_obj.rotation[5],
            0.0,
            bond_obj.rotation[6],
            bond_obj.rotation[7],
            bond_obj.rotation[8],
            0.0, 
            0.0, 0.0, 0.0, 1.0
        );
        bond_mesh.applyMatrix4(m);
        bond_mesh.position.x = bond_obj.centre[0];
        bond_mesh.position.y = bond_obj.centre[1];
        bond_mesh.position.z = bond_obj.centre[2];
        structureRoot.add(bond_mesh);
    }
    var direction = new THREE.Vector3(camera_pos0[0], camera_pos0[1], camera_pos0[2] );
    direction.normalize();
    structureRoot.rotateOnAxis(direction, structure_obj.default.structure_rotation0); 

    //////////////////////////////////////////////////////////////////////////////////
    //		render the whole thing on the page
    //////////////////////////////////////////////////////////////////////////////////

    // render the scene
    onRenderFcts.push(function(){{
        renderer.render( scene, camera );
    }})

    // run the rendering loop
    var lastTimeMsec= null
    requestAnimationFrame(function animate(nowMsec){{
        // keep looping
        requestAnimationFrame( animate );
        // measure time
        lastTimeMsec	= lastTimeMsec || nowMsec-1000/60
        var deltaMsec	= Math.min(200, nowMsec - lastTimeMsec)
        lastTimeMsec	= nowMsec
        controls.update();
        onRenderFcts.forEach(function(onRenderFct){{
            onRenderFct(deltaMsec/1000, nowMsec/1000)
        }})
    }})
}