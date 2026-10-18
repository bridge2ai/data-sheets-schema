from pathlib import Path
import html
from PIL import Image, ImageDraw, ImageFont
O = Path(__file__).resolve().parent
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'

class Canvas:
 def __init__(self,w,h,title,sub):
  self.w=w;self.h=h;self.im=Image.new('RGB',(w,h),'white');self.d=ImageDraw.Draw(self.im);self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}"><rect width="100%" height="100%" fill="white"/>'];self.text(30,20,title,27,bold=True);self.text(30,62,sub,16,color='#526277')
 def text(self,x,y,t,size=16,color='#172033',bold=False):
  self.d.text((x,y),str(t),font=ImageFont.truetype(BOLD if bold else FONT,size),fill=color);self.svg.append(f'<text x="{x}" y="{y+size}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}">{html.escape(str(t))}</text>')
 def rect(self,x,y,w,h,col):
  self.d.rectangle((x,y,x+w,y+h),fill=col);self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{col}"/>')
 def line(self,x,y,x2,y2,col='#ccd6df',width=1):
  self.d.line((x,y,x2,y2),fill=col,width=width);self.svg.append(f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{width}"/>')
 def circle(self,x,y,r,col):
  self.d.ellipse((x-r,y-r,x+r,y+r),fill=col);self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')
 def save(self,n):
  self.im.save(O/'figures'/f'{n}.png');(O/'figures'/f'{n}.svg').write_text(''.join(self.svg)+'</svg>')

def heat(name,title,sub,rows,cols,vals,maxval=100,dec=0,foot='',signed=False):
 left=max(285,min(510,max(map(len,rows))*8+40));cw=145;rh=38;w=max(1250,left+cw*len(cols)+45);h=180+rh*len(rows);c=Canvas(w,h,title,sub)
 for j,col in enumerate(cols):c.text(left+j*cw+5,105,col,14,bold=True)
 for i,row in enumerate(rows):
  y=137+i*rh;c.text(30,y+6,row,15)
  for j,v in enumerate(vals[i]):
   if v is None:col='#edf0f3';label='N/A';t=0
   else:
    t=min(abs(v)/maxval,1);end=(191,85,67) if signed and v<0 else (23,121,148);col='#%02x%02x%02x'%tuple(int(245*(1-t)+e*t) for e in end);label=f'{v:+.{dec}f}' if signed else f'{v:.{dec}f}'
   c.rect(left+j*cw,y,cw-3,rh-3,col);c.text(left+j*cw+15,y+6,label,16,color='white' if t>.7 else '#172033')
 c.text(30,h-27,foot,14);c.save(name)

def stacked(name,title,sub,rows,states,colors,den,foot):
 c=Canvas(1350,185+len(rows)*38,title,sub);left=340;ww=830
 for j,(state,col) in enumerate(zip(states,colors)):
  x=30+j*310;c.rect(x,101,14,14,col);c.text(x+22,97,state,15)
 for i,row in enumerate(rows):
  yy=139+i*38;c.text(30,yy+5,row['label'],15);x=left
  for state,col in zip(states,colors):
   n=row.get(state,0);w=ww*n/den
   if w:c.rect(x,yy,w,28,col)
   if w>=25:c.text(x+w/2-5,yy+4,n,15,color='white' if col not in ['#e1e8ee','#d6b867'] else '#172033')
   x+=w
  c.text(left+ww+12,yy+4,f'n={den}',14)
 c.text(30,c.h-28,foot,14);c.save(name)
