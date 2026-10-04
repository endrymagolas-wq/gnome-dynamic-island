// Shared GLSL ES 1.00 / Cogl fragment function. No texture or external assets.
uniform float waterTime;
uniform vec2 waterSize;
uniform float waterYaw;
uniform float waterPitch;
float waveHeight(vec2 p,float t){
    return sin(p.x*3.2+p.y*1.7-t*.75)*.045
         + sin(p.x*-2.4+p.y*4.1-t*1.1)*.025
         + sin(p.x*8.0+p.y*6.0+t*.5)*.008;
}
vec4 oceanPixel(vec2 uv){
    float scale=min(waterSize.x/1000.0,waterSize.y/650.0);
    vec2 screen=(uv*waterSize-waterSize*.5)/scale+vec2(500.0,325.0);
    float cy=cos(waterYaw),sy=sin(waterYaw),sp=sin(waterPitch);
    float sx=(screen.x-500.0)/105.0,sz=(screen.y-360.0)/(105.0*sp);
    vec2 p=vec2(cy*sx+sy*sz,-sy*sx+cy*sz);
    float t=waterTime;
    float eps=.03,h=waveHeight(p,t);
    vec3 n=normalize(vec3((h-waveHeight(p+vec2(eps,0.0),t))/eps,1.0,(h-waveHeight(p+vec2(0.0,eps),t))/eps));
    vec2 coast=p/vec2(3.1,2.25);
    float angle=atan(coast.y,coast.x);
    float radial=length(coast)/(1.0+.035*sin(angle*5.0)+.025*cos(angle*7.0));
    float shore=1.0-smoothstep(1.00,1.42,radial);
    vec3 deep=vec3(.065,.35,.43),shallow=vec3(.19,.66,.65);
    vec3 color=mix(deep,shallow,shore);
    float diffuse=max(0.0,dot(n,normalize(vec3(-.38,.82,.43))));
    color*=.8+.25*diffuse;
    color+=vec3(.035,.055,.055)*sin(p.x*5.0+p.y*3.0-t*.65)*.5;
    // Moving caustic threads in shallow water.
    float caustic=pow(max(0.0,sin(p.x*13.0+sin(p.y*9.0+t)*1.2+t*.45)*sin(p.y*14.0-p.x*3.0-t*.35)),8.0);
    color+=vec3(.11,.20,.13)*caustic*shore;
    // Fresnel tint and a narrow sun-glint across wave normals.
    vec3 view=normalize(vec3(sy*cos(waterPitch),sin(waterPitch),cy*cos(waterPitch)));
    vec3 halfVector=normalize(normalize(vec3(-.38,.82,.43))+view);
    float specular=pow(max(0.0,dot(n,halfVector)),95.0);
    float fresnel=pow(1.0-max(0.0,dot(n,view)),3.0);
    color=mix(color,vec3(.57,.77,.78),fresnel*.25);
    color+=vec3(1.0,.89,.64)*specular*.8;
    // Two moving foam ribbons around the actual island radius.
    float ring=abs(radial-(1.055+.016*sin(t*1.2+p.x*2.0)));
    float foam=(1.0-smoothstep(.009,.035,ring))*(.55+.45*sin(p.x*17.0+p.y*19.0+t*.6));
    float ring2=abs(radial-(1.19+.025*sin(t*.9)));
    foam+=.28*(1.0-smoothstep(.008,.025,ring2));
    color=mix(color,vec3(.79,.94,.84),clamp(foam,0.0,.7));
    // Soft distance haze and vignette keep the desktop calm.
    color=mix(color,vec3(.34,.57,.60),smoothstep(3.0,12.0,length(p))*.38);
    color*=1.0-.16*smoothstep(.3,.8,length(uv-.5));
    return vec4(color,1.0);
}
