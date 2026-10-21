/** Only the range containing the playhead contributes; never sum across gaps. */
export function playableBuffer(ranges:TimeRanges,time:number):number {
  for(let i=0;i<ranges.length;i++)if(ranges.start(i)<=time+.03&&ranges.end(i)>time)return Math.max(0,ranges.end(i)-time);
  return 0;
}
