vec4 layerPixel(sampler2D source, vec2 uv, vec2 sourceCrop) {
    return texture2D(source, clamp((uv-.5)/sourceCrop+.5,vec2(0.0),vec2(1.0)));
}
vec2 layerPosition(vec2 uv, float phase, float energy, float strength, float id) {
    float anchor = sin(3.14159265*uv.x)*sin(3.14159265*uv.y);
    // High frequencies get less displacement, never quicker motion.
    float amplitude = energy*mix(.019,.0085,id/3.0)*strength;
    float broad = sin(uv.x*(4.5+id*.7)-phase+id*.6);
    float secondary = sin(uv.x*7.2+uv.y*2.0+phase*.38+id*1.7);
    return clamp(uv+vec2(0.0,(broad*.82+secondary*.18)*amplitude*anchor),vec2(0.0),vec2(1.0));
}
vec4 sceneTint(vec4 color,float phase,float amount,float direction){
    if(amount<.00001)return color;
    float luminance=dot(color.rgb,vec3(.299,.587,.114));
    vec3 rgb=mix(vec3(luminance),color.rgb,1.0+amount*.18);
    float angle=amount*(.20+.18*sin(phase*.45))*direction;
    float y=dot(rgb,vec3(.299,.587,.114));
    float i=dot(rgb,vec3(.596,-.274,-.322));
    float q=dot(rgb,vec3(.211,-.523,.312));
    float ni=i*cos(angle)-q*sin(angle),nq=i*sin(angle)+q*cos(angle);
    return vec4(clamp(vec3(y+.956*ni+.621*nq,y-.272*ni-.647*nq,y-1.106*ni+1.703*nq),0.0,1.0),color.a);
}
vec4 layeredColor(sampler2D source,vec2 uv,vec2 sourceCrop,vec4 phases,vec4 bands,float strength,float palette) {
    vec4 original=layerPixel(source,uv,sourceCrop);
    float activity=max(max(bands.x,bands.y),max(bands.z,bands.w));
    if(activity<.00001)return original;
    vec2 blue=layerPosition(uv,phases.w,bands.w,strength,3.0);
    vec2 pearl=layerPosition(uv,phases.z,bands.z,strength,2.0);
    vec2 amber=layerPosition(uv,phases.y,bands.y,strength,1.0);
    vec2 red=layerPosition(uv,phases.x,bands.x,strength,0.0);
    // Extend each original color behind its own boundary before compositing.
    // Overlapping feather zones sample the original pixels, preserving gradients.
    float be=blueEdge(blue.x),pb=blueEdge(pearl.x),pa=amberEdge(pearl.x);
    float ab=amberEdge(amber.x),ar=redEdge(amber.x),re=redEdge(red.x);
    vec4 color=layerPixel(source,vec2(blue.x,min(blue.y,be+.0015)),sourceCrop);
    vec4 whiteColor=layerPixel(source,vec2(pearl.x,clamp(pearl.y,pb-.002,max(pb-.002,pa+.045))),sourceCrop);
    color=sceneTint(color,phases.w,palette,1.0);
    whiteColor=sceneTint(whiteColor,phases.z,palette*.25,.4);
    color=mix(color,whiteColor,smoothstep(pb-.001,pb+.001,pearl.y));
    vec4 amberColor=layerPixel(source,vec2(amber.x,clamp(amber.y,ab-.045,max(ab-.045,ar+.002))),sourceCrop);
    amberColor=sceneTint(amberColor,phases.y,palette,.55);
    color=mix(color,amberColor,smoothstep(ab-.035,ab+.035,amber.y));
    vec4 redColor=layerPixel(source,vec2(red.x,max(red.y,re-.002)),sourceCrop);
    redColor=sceneTint(redColor,phases.x,palette,-.9);
    color=mix(color,redColor,smoothstep(re-.0008,re+.0008,red.y));
    // No visual jump when starting or stopping quiet playback.
    return mix(original,color,smoothstep(0.0,.12,activity));
}
