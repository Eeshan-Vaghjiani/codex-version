import{P as e,Q as t,Z as n,j as r,pt as i,s as a,t as o,y as s}from"./SeriesRegistry-D9skVCBF.js";import"./coloraxis.src-yfZGk3z-.js";import{t as c}from"./CrossSymbol-B5TfWf9K.js";var{scatter:{prototype:{pointClass:l}}}=o.seriesTypes,u=class extends l{},d=`

struct VertexInput {
    @location(0) pos: vec3f
}

struct VertexOutput {
    @builtin(position) pos: vec4f,
    @location(0) originalPos: vec3f,
    @location(1) valExtremes: vec2f,
}

@group(0) @binding(0) var<uniform> uExtremes: vec4f;
@group(0) @binding(1) var<uniform> uValueExtremes: vec2f;
@group(0) @binding(9) var<uniform> uIsInverted: u32;

@vertex
fn vertexMain(input: VertexInput) -> VertexOutput {
    var output: VertexOutput;
    let pos = input.pos;

    let xMin = uExtremes[0];
    let xMax = uExtremes[1];
    let yMin = uExtremes[2];
    let yMax = uExtremes[3];

    var posX: f32;
    var posY: f32;
    if (uIsInverted > 0u) {
        posX = (1.0 - (pos.y - yMin) / (yMax - yMin)) * 2.0 - 1.0;
        posY = (1.0 - (pos.x - xMin) / (xMax - xMin)) * 2.0 - 1.0;
    } else {
        posX = (pos.x - xMin) / (xMax - xMin) * 2.0 - 1.0;
        posY = (pos.y - yMin) / (yMax - yMin) * 2.0 - 1.0;
    }

    output.valExtremes = uValueExtremes;
    output.originalPos = pos.xyz;
    output.pos = vec4f(posX, posY, 0, 1);

    return output;
}

// ------------------------------------------------

struct FragmentInput {
    @location(0) originalPos: vec3f,
    @location(1) valExtremes: vec2f
}

@group(0) @binding(2) var<storage> uColorStops: array<vec4<f32>>;
@group(0) @binding(3) var<uniform> uColorStopsCount: u32;
@group(0) @binding(4) var<uniform> uContourInterval: f32;
@group(0) @binding(5) var<uniform> uContourOffset: f32;
@group(0) @binding(6) var<uniform> uSmoothColoring: u32;
@group(0) @binding(7) var<uniform> uContourLineWidth: f32;
@group(0) @binding(8) var<uniform> uContourLineColor: vec3f;

fn getColor(value: f32) -> vec3<f32> {
    let stopCount = uColorStopsCount;

    if (stopCount == 0u) {
        return vec3<f32>(1.0, 1.0, 1.0);
    }

    for (var i: u32 = 0u; i < stopCount - 1u; i = i + 1u) {
        if (value < uColorStops[i + 1u].x) {
            let t = (value - uColorStops[i].x) /
                (uColorStops[i + 1u].x - uColorStops[i].x);

            return mix(uColorStops[i].yzw, uColorStops[i + 1u].yzw, t);
        }
    }

    return uColorStops[stopCount - 1u].yzw;
}

@fragment
fn fragmentMain(input: FragmentInput) -> @location(0) vec4f {
    let val = input.originalPos.z;

    // Contour lines
    let lineWidth: f32 = uContourLineWidth;

    let val_dx: f32 = dpdx(val);
    let val_dy: f32 = dpdy(val);
    let gradient: f32 = length(vec2f(val_dx, val_dy));

    let epsilon: f32 = max(uContourInterval * 1.0e-6, 1.0e-12);
    let adjustedLineWidth: f32 = lineWidth * gradient + epsilon;

    let adjustedVal: f32 = val - uContourOffset;
    let valDiv: f32 = adjustedVal / uContourInterval;
    let valMod: f32 = adjustedVal - uContourInterval * floor(valDiv);

    let lineMask: f32 = smoothstep(0.0, adjustedLineWidth, valMod) * (
        1.0 - smoothstep(
            uContourInterval - adjustedLineWidth,
            uContourInterval,
            valMod
        )
    );

    // Background color
    let minHeight: f32 = input.valExtremes.x;
    let maxHeight: f32 = input.valExtremes.y;

    var bgColor: vec3f;
    if (uSmoothColoring > 0u) {
        bgColor = getColor((val - minHeight) / (maxHeight - minHeight));
    } else {
        let adjustedVal: f32 = val - uContourOffset;
        let averageValInBand: f32 = floor(
            adjustedVal / uContourInterval
        ) * uContourInterval + uContourOffset + uContourInterval / 2.0;

        bgColor = getColor(
            (averageValInBand - minHeight) /
            (maxHeight - minHeight)
        );
    }

    // Mix
    var pixelColor = bgColor;
    if (lineWidth > 0.0) {
        pixelColor = mix(uContourLineColor, pixelColor, lineMask);
    }

    return vec4(pixelColor, 1.0);
}

`,f={colorKey:`value`,clip:!1,marker:{symbol:`cross`,states:{hover:{lineColor:`black`}}},states:{hover:{halo:void 0}},zIndex:0},p=class{constructor(e){this.points=e;let t=e.length>>>1;this.epsilon=4*2**-52;let n=1/0,r=-1/0,i=1/0,a=-1/0;for(let o=0;o<t;o++){let t=e[o<<1],s=e[(o<<1)+1];t<n&&(n=t),t>r&&(r=t),s<i&&(i=s),s>a&&(a=s)}let o=r-n||1,s=a-i||1;this.minX=n,this.minY=i,this.invScaleX=1/o,this.invScaleY=1/s;let c=new Uint32Array(t),l=t=>(e[t<<1]-n)*this.invScaleX,u=t=>(e[(t<<1)+1]-i)*this.invScaleY;for(let e=0;e<t;e++)c[e]=e;c.sort((e,t)=>l(e)-l(t)||u(e)-u(t));let d=+!!t,f,p;for(let e=1;e<t;++e)f=c[d-1],p=c[e],(l(f)!==l(p)||u(f)!==u(p))&&(c[d++]=p);this.ids=c.subarray(0,d),this.triangles=this.triangulate()}triangulate(){let e=this.ids.length;if(e<3)return new Uint32Array;let t=this.points,{minX:n,minY:r,invScaleX:i,invScaleY:a}=this,o=e=>(t[e<<1]-n)*i,s=e=>(t[(e<<1)+1]-r)*a,c=(e,t,n)=>{let r=o(e),i=s(e),a=o(t)-r,c=s(t)-i,l=o(n)-r,u=s(n)-i;return a*u-c*l>(Math.abs(a*u)+Math.abs(c*l))*this.epsilon},l=(e,t,n,r)=>{if(e===r||t===r||n===r)return!1;let i=o(e)-o(r),a=s(e)-s(r),c=o(t)-o(r),l=s(t)-s(r),u=o(n)-o(r),d=s(n)-s(r),f=i*i+a*a,p=c*c+l*l,m=u*u+d*d,h=l*m-p*d,g=c*m-p*u,_=c*d-l*u;return i*h-a*g+f*_>(Math.abs(i*h)+Math.abs(a*g)+Math.abs(f*_))*this.epsilon},u=Math.max(32,8*e+7&-4),d=new Int32Array(u),f=new Int32Array(u),p=new Uint32Array(u),m=new Uint8Array(u),h=0,g=e=>{if(e<=u)return;let t=u<<1;for(;t<e;)t<<=1;let n=new Int32Array(t),r=new Int32Array(t),i=new Uint32Array(t),a=new Uint8Array(t);n.set(d),r.set(f),i.set(p),a.set(m),d=n,f=r,p=i,m=a,u=t},_=e=>f[f[e]],v=e=>_(f[e]),y=e=>p[_(e)],b=e=>f[d[v(e)]],x=e=>f[d[f[e]]],S=e=>d[_(e)],C=(e,t)=>c(e,p[t],y(t)),w=(e,t)=>c(e,y(t),p[t]),T=(e,t)=>w(y(e),t),E=(e,t)=>{g(h+4);let n=h,r=h+1,i=h+2,a=h+3;return h+=4,f[n]=r,f[r]=i,f[i]=a,f[a]=n,d[n]=n,d[i]=i,d[r]=a,d[a]=r,p[n]=e,p[i]=t,p[r]=4294967295,p[a]=4294967295,n},D=(e,t)=>{let n=f[d[e]],r=f[d[t]],i=d[e],a=d[r],o=d[n];d[e]=d[t],d[t]=i,d[n]=a,d[r]=o},O=(e,t)=>{let n=E(y(e),p[t]);return D(n,b(e)),D(_(n),t),n},k=e=>{D(e,x(e));let t=_(e);D(t,x(t))},A=this.ids,j=(e,t)=>{let n=t-e;if(n===2){let t=E(A[e],A[e+1]);return[t,_(t)]}if(n===3){let t=E(A[e],A[e+1]),n=E(A[e+1],A[e+2]);D(_(t),n);let r=A[e],i=A[e+1],a=A[e+2];if(c(r,i,a))return O(n,t),[t,_(n)];if(c(r,a,i)){let e=O(n,t);return[_(e),e]}return[t,_(n)]}let r=e+(n+1>>>1),i=j(e,r),a=j(r,t),o=i[0],s=i[1],u=a[0],f=a[1];for(;;)if(C(p[u],s))s=b(s);else if(w(p[s],u))u=S(u);else break;let m=O(_(u),s);for(p[s]===p[o]&&(o=_(m)),p[u]===p[f]&&(f=m);;){let e=d[_(m)];if(T(e,m))for(;l(y(m),p[m],y(e),y(d[e]));){let t=d[e];k(e),e=t}let t=x(m);if(T(t,m))for(;l(y(m),p[m],y(t),y(x(t)));){let e=x(t);k(t),t=e}if(!T(e,m)&&!T(t,m))break;m=!T(e,m)||T(t,m)&&l(y(e),p[e],p[t],y(t))?O(t,_(m)):O(_(m),_(e))}return[o,f]},M=j(0,e)[0];for(;C(y(d[M]),M);)M=d[M];let N=[M],P=0;{let e=M;do N.push(_(e)),m[e]=1,e=b(e);while(e!==M)}let F=[],I,L;for(;P<N.length;){let e=N[P++];if(!m[e]){I=e;do F.push(p[I]),L=_(I),m[L]||N.push(L),m[I]=1,I=b(I);while(I!==e)}}return new Uint32Array(F)}},{seriesTypes:{scatter:m}}=o,h=class e extends m{static compose(e){c.compose(e)}getContourData(){let e=this.points,t=e.length,n=new Float32Array(t*3),r=new Float64Array(t*2);for(let i=0;i<t;i++){let{x:t,y:a=0,value:o}=e[i],s=i*2,c=i*3;r[s]=t,r[s+1]=a,n[c]=t,n[c+1]=a,n[c+2]=o??0}return[new p(r).triangles,n]}update(e,t){e=r(e,this.userOptions);let i=[`smoothColoring`,`contourInterval`,`contourOffset`,`lineColor`,`lineWidth`],a=e=>i.includes(e),o=Object.keys(e).some(e=>!a(e)),s=o?void 0:this.setOptions(n(this.userOptions,e)),c=s?Object.keys(r(s,this.options)).some(e=>!a(e)):!1;o||c?super.update(e,t):(this.options=s,this.setUniforms())}drawPoints(){let{group:e}=this;if(!e)return;this.canvas||(this.foreignObject=document.createElementNS(`http://www.w3.org/2000/svg`,`foreignObject`),e.element.appendChild(this.foreignObject),this.canvas=document.createElement(`canvas`),this.foreignObject.appendChild(this.canvas));let{canvas:t,xAxis:n,yAxis:r}=this,i=this.foreignObject,a=i.width.baseVal.value,o=i.height.baseVal.value,{devicePixelRatio:s}=window,c=n.len,l=r.len;this.chart.inverted&&([c,l]=[l,c]),a!==c&&(i.setAttribute(`width`,c),t.width=c*s,t.style.width=c+`px`),o!==l&&(i.setAttribute(`height`,l),t.height=l*s,t.style.height=l+`px`),this.renderFrame?this.renderFrame():this.run()}async run(){let e=this,t=e.chart,n=t.renderer,r=e.canvas,i=navigator.gpu,o=e.context=r.getContext(`webgpu`);if(!i||!o)a(37,!1,t);else{if(n.asyncCounter+=1,o){let e=this.device;this.adapter||=await i.requestAdapter(),!e&&this.adapter&&(e=this.device=await this.adapter.requestDevice());let t=i.getPreferredCanvasFormat();if(e){o.configure({device:e,format:t,colorSpace:`display-p3`,alphaMode:`premultiplied`,usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.COPY_SRC});let[n,r]=this.getContourData(),{vertex:i,index:a,extremesUniform:s,valueExtremesUniform:c,contourIntervalUniform:l,contourOffsetUniform:u,smoothColoringUniform:f,lineWidthUniform:p,contourLineColor:m,colorAxisStopsCountUniform:h,colorAxisStopsUniform:g,isInvertedUniform:_}=this.buffers={vertex:e.createBuffer({size:r.byteLength,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST}),index:e.createBuffer({size:n.byteLength,usage:GPUBufferUsage.INDEX|GPUBufferUsage.COPY_DST}),extremesUniform:e.createBuffer({size:Float32Array.BYTES_PER_ELEMENT*4,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST}),valueExtremesUniform:e.createBuffer({size:Float32Array.BYTES_PER_ELEMENT*2,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST}),contourIntervalUniform:e.createBuffer({size:4,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST}),contourOffsetUniform:e.createBuffer({size:4,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST}),smoothColoringUniform:e.createBuffer({size:4,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST}),lineWidthUniform:e.createBuffer({size:4,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST}),contourLineColor:e.createBuffer({size:12,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST}),colorAxisStopsCountUniform:e.createBuffer({size:4,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST}),colorAxisStopsUniform:e.createBuffer({size:Float32Array.BYTES_PER_ELEMENT*64,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST}),isInvertedUniform:e.createBuffer({size:4,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST})};e.queue.writeBuffer(i,0,r),e.queue.writeBuffer(a,0,n);let v={arrayStride:12,attributes:[{format:`float32x3`,offset:0,shaderLocation:0}]},y=e.createShaderModule({code:d}),b=e.createRenderPipeline({layout:`auto`,vertex:{module:y,entryPoint:`vertexMain`,buffers:[v]},fragment:{module:y,entryPoint:`fragmentMain`,targets:[{format:t}]},primitive:{topology:`triangle-list`}}),x=e.createBindGroup({layout:b.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:s,label:`extremesUniformBuffer`}},{binding:1,resource:{buffer:c,label:`valueExtremesUniformBuffer`}},{binding:2,resource:{buffer:g,label:`colorAxisStopsBuffer`}},{binding:3,resource:{buffer:h,label:`colorAxisStopsCountBuffer`}},{binding:4,resource:{buffer:l,label:`contourIntervalUniformBuffer`}},{binding:5,resource:{buffer:u,label:`contourOffsetUniformBuffer`}},{binding:6,resource:{buffer:f,label:`smoothColoringUniformBuffer`}},{binding:7,resource:{buffer:p,label:`lineWidthUniformBuffer`}},{binding:8,resource:{buffer:m,label:`contourLineColorBuffer`}},{binding:9,resource:{buffer:_,label:`isInvertedUniformBuffer`}}]});this.renderFrame=function(){this.setUniforms(!1);let t=e.createCommandEncoder(),r=o.getCurrentTexture(),s=t.beginRenderPass({colorAttachments:[{view:r.createView(),loadOp:`clear`,clearValue:[0,0,0,0],storeOp:`store`}]});s.setPipeline(b),s.setVertexBuffer(0,i),s.setIndexBuffer(a,`uint32`),s.setBindGroup(0,x),s.drawIndexed(n.length),s.end(),e.queue.submit([t.finish()])},this.renderFrame()}}n.asyncCounter--,!n.asyncCounter&&t&&!t.hasLoaded&&t.onload()}}destroy(){this.canvas?.parentElement?.remove(),super.destroy()}drawGraph(){}setUniforms(e=!0){this.setFrameExtremesUniform(!1),this.setValueExtremesUniform(!1),this.setColorAxisStopsUniforms(!1),this.setContourIntervalUniform(!1),this.setContourOffsetUniform(!1),this.setSmoothColoringUniform(!1),this.setLineWidthUniform(!1),this.setContourLineColorUniform(!1),this.setIsInvertedUniform(e)}setContourIntervalUniform(e=!0){this.device&&this.buffers?.contourIntervalUniform&&(this.device.queue.writeBuffer(this.buffers.contourIntervalUniform,0,new Float32Array([this.getContourInterval()])),e&&this.renderFrame?.())}setContourOffsetUniform(e=!0){this.device&&this.buffers?.contourOffsetUniform&&(this.device.queue.writeBuffer(this.buffers.contourOffsetUniform,0,new Float32Array([this.getContourOffset()])),e&&this.renderFrame?.())}setSmoothColoringUniform(e=!0){this.device&&this.buffers?.smoothColoringUniform&&(this.device.queue.writeBuffer(this.buffers.smoothColoringUniform,0,new Float32Array([this.getSmoothColoring()])),e&&this.renderFrame?.())}setLineWidthUniform(e=!0){this.device&&this.buffers?.lineWidthUniform&&(this.device.queue.writeBuffer(this.buffers.lineWidthUniform,0,new Float32Array([this.getLineWidth()])),e&&this.renderFrame?.())}setContourLineColorUniform(e=!0){this.device&&this.buffers?.contourLineColor&&(this.device.queue.writeBuffer(this.buffers.contourLineColor,0,new Float32Array(this.getContourLineColor())),e&&this.renderFrame?.())}setFrameExtremesUniform(e=!0){this.device&&this.buffers?.extremesUniform&&(this.device.queue.writeBuffer(this.buffers.extremesUniform,0,new Float32Array(this.getFrameExtremes())),e&&this.renderFrame?.())}setValueExtremesUniform(e=!0){this.device&&this.buffers?.valueExtremesUniform&&(this.device.queue.writeBuffer(this.buffers.valueExtremesUniform,0,new Float32Array(this.getValueAxisExtremes())),e&&this.renderFrame?.())}setColorAxisStopsUniforms(e=!0){let t=this.buffers?.colorAxisStopsUniform,n=this.buffers?.colorAxisStopsCountUniform;if(this.device&&t&&n){let{array:r,length:i}=this.getColorAxisStopsData();this.device.queue.writeBuffer(t,0,r),this.device.queue.writeBuffer(n,0,new Uint32Array([i])),e&&this.renderFrame?.()}}setIsInvertedUniform(e=!0){this.device&&this.buffers?.isInvertedUniform&&(this.device.queue.writeBuffer(this.buffers.isInvertedUniform,0,new Uint32Array([+!!this.chart.inverted])),e&&this.renderFrame?.())}getContourInterval(){let e=this.options.contourInterval??(()=>{let[e,n]=this.getValueAxisExtremes(),r=n-e;return t(r/10)})();return isNaN(e)||e<=0?-1:e}getContourOffset(){let e=this.options.contourOffset??0;return isNaN(e)||e<=0?0:e}getSmoothColoring(){return+!!this.options.smoothColoring}getLineWidth(){return this.userOptions.lineWidth??1}getContourLineColor(){let{lineColor:t=`#000000`}=this.options;return e.rgbaAsFrac(new s(t).rgba)}getFrameExtremes(){let{xAxis:e,yAxis:t}=this;return[e.toValue(0,!0),e.toValue(e.len,!0),t.toValue(t.len,!0),t.toValue(0,!0)]}getValueAxisExtremes(){let e=this,t=e.valueMin;isNaN(t||NaN)&&(t=e.colorAxis?.min,isNaN(t||NaN)&&(t=Math.min(...e.points.map(e=>e.value||0))));let n=e.valueMax;return isNaN(n||NaN)&&(n=e.colorAxis?.max,isNaN(n||NaN)&&(n=Math.max(...e.points.map(e=>e.value||0)))),[t||0,n||0]}getColorAxisStopsData(){let t=this.colorAxis?.stops,n;if(t){n=[];for(let r of t){let t=r?.color?.rgba;t&&n.push(r[0],...e.rgbaAsFrac(t))}}return{array:new Float32Array(n??[0,0,0,0,1,1,1,1]),length:t?.length||2}}static rgbaAsFrac(e){return[e[0],e[1],e[2]].map(e=>e/255)}};h.defaultOptions=n(m.defaultOptions,f),e(h.prototype,{pointClass:u,pointArrayMap:[`y`,`value`],keysAffectYAxis:[`y`],invertible:!1}),o.registerSeriesType(`contour`,h);var g=i;h.compose(g.Renderer);