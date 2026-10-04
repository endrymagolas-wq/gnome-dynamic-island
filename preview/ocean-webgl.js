/** The exact same ocean fragment function used by the GNOME GLSL effect. */
export async function createOcean(canvas, camera){
    const gl=canvas.getContext('webgl',{alpha:false,antialias:false,preserveDrawingBuffer:true});
    if(!gl)throw new Error('WebGL недоступний');
    const response=await fetch('../extensions/cartoon-island@avalon.local/ocean.glsl');
    if(!response.ok)throw new Error('Не вдалося завантажити шейдер води');
    const source=await response.text();
    const compile=(type,text)=>{const shader=gl.createShader(type);gl.shaderSource(shader,text);gl.compileShader(shader);if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(shader));return shader;};
    const program=gl.createProgram();
    gl.attachShader(program,compile(gl.VERTEX_SHADER,'attribute vec2 position;varying vec2 uv;void main(){uv=(position+1.0)*.5;gl_Position=vec4(position,0.0,1.0);}'));
    gl.attachShader(program,compile(gl.FRAGMENT_SHADER,'precision highp float;varying vec2 uv;\n'+source+'\nvoid main(){gl_FragColor=oceanPixel(vec2(uv.x,1.0-uv.y));}'));
    gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);
    const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
    const position=gl.getAttribLocation(program,'position');gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
    const uniforms=Object.fromEntries(['waterTime','waterSize','waterYaw','waterPitch'].map(key=>[key,gl.getUniformLocation(program,key)]));
    return {draw(time){gl.viewport(0,0,canvas.width,canvas.height);gl.useProgram(program);gl.uniform1f(uniforms.waterTime,time);gl.uniform2f(uniforms.waterSize,canvas.width,canvas.height);gl.uniform1f(uniforms.waterYaw,camera.yaw);gl.uniform1f(uniforms.waterPitch,camera.pitch);gl.drawArrays(gl.TRIANGLES,0,6);},gl};
}
