//+------------------------------------------------------------------+
//|                                                      ProjectName |
//|                                      Copyright 2018, CompanyName |
//|                                       http://www.companyname.net |
//+------------------------------------------------------------------+
#property strict
#property copyright "QQ160937125"

#property indicator_chart_window
#property indicator_buffers 17

#property indicator_type1   DRAW_LINE
#property indicator_style1  STYLE_SOLID
#property indicator_type2   DRAW_LINE
#property indicator_style2  STYLE_SOLID
#property indicator_type3   DRAW_LINE
#property indicator_style3  STYLE_DASH
#property indicator_type4   DRAW_LINE
#property indicator_style4  STYLE_DASH
#property indicator_type5   DRAW_LINE
#property indicator_style5  STYLE_SOLID
#property indicator_type6   DRAW_LINE
#property indicator_style6  STYLE_SOLID

enum ENGBOOLEAN
  {
   A=0,//On
   B=1,//Off
  };
#property copyright "samirliu"

string AlertVariables="==========";
ENGBOOLEAN PopupAlert=B;
ENGBOOLEAN SoundAlert=B;
ENGBOOLEAN MailAlert=B;
ENGBOOLEAN MobileAlert=B;
int nBarMax=2000;
string ColorVariables="==========";
color UpTrendChannelColor=clrMaroon;
color DownTrendChannelColor=clrDarkGreen;
color SideWayChannelColor=clrGray;
color BeltColor=C'0x55,0x55,0x55';
color BUY_TextColor=clrRed;
color SELL_TextColor=clrLime;
color CLOSE_BUY_TextColor=clrYellow;
color CLOSE_SELL_TextColor=clrYellow;
color SL_BUY_TextColor=clrRed;
color SL_SELL_TextColor=clrLime;
color Line1Color=clrWhite;
color Line2Color=clrWhite;
color Line3Color=clrRed;
color Line4Color=clrLime;
color Line5Color=clrGray;
color Line6Color=clrGray;

bool bError=false,isChs=false;
int iBarMax=2000,iBarMin=50,sh=30,indC=0,indCMax=3,
    fsx=12,fsc=12,fse=9,kNoAlert=3;
datetime dtInd=0,dtAlertBuy,dtAlertSell,dtAlertCloseBuy,dtAlertCloseSell;
string strEA=MQLInfoString(MQL_PROGRAM_NAME),strFt,strFth="??",
       strFte="Arial";
///
double gd_unused_88 = 12.0;
double gd_unused_96 = 31.0;
double gd_unused_104 = 24.0;
int g_width_112 = 8;
double g_ibuf_116[];
double g_ibuf_120[];
double g_ibuf_124[];
double g_ibuf_128[];
double g_ibuf_132[];
double g_ibuf_136[];
double slld_0[],slld_8[];
int gi_unused_140 = 0;
int gi_unused_144 = 0;
double xma148_25_25_3_0[],xma148_25_25_2_0[],xma148_25_25_3_1[],xma148_25_25_2_1[];
double belt156_0[],belt156_1[],belt156_2[],belt156_3[],belt156_4[];
int xma148_25_25_3_N=25,xma148_25_25_3_N1=25,xma148_25_25_3_mode=3,
    xma148_25_25_2_N=25,xma148_25_25_2_N1=25,xma148_25_25_2_mode=2;
input int Shift = 30; // 回溯偏移量，0 表示当前，30 表示向前推 30 根K线
///
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+

bool EnableLogging = true;  // 设置为false可关闭日志
string LogFileName = "shenlong_log.txt";
//+------------------------------------------------------------------+
//| 写日志函数（自动追加到文件末尾）                                |
//+------------------------------------------------------------------+
void WriteLog(string message)
{
    if(!EnableLogging) return;

    int handle = FileOpen(LogFileName,
                          FILE_READ | FILE_WRITE | FILE_TXT | FILE_COMMON);

    if(handle != INVALID_HANDLE)
    {
        // 写入末尾
        FileSeek(handle, 0, SEEK_END);

        string timestamp = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);
        FileWrite(handle, timestamp + " - " + message);

        FileClose(handle);
    }
    else
    {
        Print("日志文件无法打开: ", LogFileName);
    }
}


int OnInit()
  {
  WriteLog("OnInit() started");
   strEA=StringSubstr(strEA,0,StringFind(strEA,"(",0));
   if(CheckIniError())
      return (INIT_FAILED);
   if(!bError)
      IndicatorIni();
   ChartRedraw();
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   ObjectsDeleteAll(0,strEA);
   ChartRedraw();
  }
//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
  {
   if(bError)
      return-1;
       if(prev_calculated == 0) {
      WriteLog("=== 开始计算神龙通道指标 ===");
      WriteLog("数据总数: "+ rates_total + ", 先前计算: " + prev_calculated);
   }
   DrawInd(rates_total,prev_calculated);
   return(rates_total);
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void DrawInd(int rates_total,int prev_calculated)
  {

   int ii,limit,limitXma_25_25_3,limitXma_25_25_2;
   bool bIndIni=prev_calculated<=0 || indC<indCMax || dtInd!=PriceShift(4,0) || IndicatorCounted()==0;
   if(bIndIni)
     {
      ArrayIni(((indC>0 && dtInd==PriceShift(4,0)) || IndicatorCounted()==0)?true:false);
      limit=(rates_total<iBarMax)?rates_total-sh:iBarMax-sh;
      limitXma_25_25_3=limit;
      limitXma_25_25_2=limit;
     }
   else
     {
      limit=(rates_total<iBarMin)?rates_total-sh:iBarMin-sh;
      limitXma_25_25_3=(int)MathMax(xma148_25_25_3_N,xma148_25_25_3_N1)+2;
      limitXma_25_25_3=(limitXma_25_25_3>rates_total)?rates_total-1:limitXma_25_25_3;
      limitXma_25_25_2=(int)MathMax(xma148_25_25_2_N,xma148_25_25_2_N1)+2;
      limitXma_25_25_2=(limitXma_25_25_2>rates_total)?rates_total-1:limitXma_25_25_2;
     }
       datetime current_time = iTime(Symbol(), Period(), 0);
   WriteLog("当前时间: " + TimeToString(current_time) + ", 计算范围: 0-" + limit);
///MHDMT_GRAY_BELT.mq4
   int li_48=0;
   bool li_16=false,li_20=false;
   if(bIndIni)
     {
      for(ii=limit-1; ii>=0; ii--)
        {
         if(ii+20>=rates_total)
            continue;
         double sum_high = 0;   
         for(int w=0; w<=20; w++) {
            sum_high += (20.0 - w) * PriceShift(2,ii + w);
         }
         belt156_0[ii] = sum_high / 210.0;
         // 记录belt1计算
         double sum_low = 0;
         for(int w=0; w<=20; w++) {
            sum_low += (20.0 - w) * PriceShift(3,ii + w);
         }
         belt156_1[ii] = sum_low / 210.0;
      //   WriteLog("Time=" + TimeToString(iTime(Symbol(),Period(),ii), TIME_DATE|TIME_MINUTES|TIME_SECONDS) + 
      //   ",Bar " + IntegerToString(ii) + ",belt156_0: " + DoubleToString(belt156_0[ii]) + ",belt156_1: " + DoubleToString(belt156_1[ii]));
        }
              // if(ii <= 3) {
           // WriteLog("Bar " + IntegerToString(ii) + " (" + TimeToString(iTime(Symbol(),Period(),ii)) + "): ");
        //    WriteLog("  High data: " + DoubleToString(iHigh(Symbol(),Period(),ii), 4) + " to " + DoubleToString(iHigh(Symbol(),Period(),ii+20), 4));
        //    WriteLog("  Low data: " + DoubleToString(iLow(Symbol(),Period(),ii), 4) + " to " + DoubleToString(iLow(Symbol(),Period(),ii+20), 4));
        //    WriteLog("  belt0 = " + DoubleToString(belt156_0[ii], 6) + ", belt1 = " + DoubleToString(belt156_1[ii], 6));
         //}
      for(ii=limit-2; ii>=0; ii--)
        {
         if(ii+1>=rates_total)
            continue;
         //WriteLog("belt156_0ii=" + DoubleToString(belt156_0[ii]) + ",belt156_2ii+1: " + DoubleToString(belt156_2[ii+1]));
         belt156_2[ii]=(2*belt156_0[ii]+(90-1)*belt156_2[ii+1])/(90+1);
         belt156_3[ii]=(2*belt156_1[ii]+(90-1)*belt156_3[ii+1])/(90+1);
         belt156_4[ii]=belt156_2[ii]-belt156_3[ii];
       //  WriteLog("Time=" + TimeToString(iTime(Symbol(),Period(),ii), TIME_DATE|TIME_MINUTES|TIME_SECONDS) + 
       //  ",Bar " + IntegerToString(ii) + ",belt156_2: " + DoubleToString(belt156_2[ii]) + ",belt156_3: " + DoubleToString(belt156_3[ii]));
        }
      ///MHDMT_XMA.mq4
      int Li_12=0,Li_20=0;
      double Ld_0=0;
      for(Li_12 = limitXma_25_25_3; Li_12 >= 0; Li_12--)
        {
         if(Li_12 >= (xma148_25_25_3_N - 1) / 2)
           {
            Ld_0 = 0;
            for(Li_20 = Li_12 + int((xma148_25_25_3_N - 1) / 2) ; Li_20 >= Li_12 - (xma148_25_25_3_N - 1) / 2; Li_20--)
              { if(Li_20>=rates_total) continue; Ld_0 += PriceShift(xma148_25_25_3_mode, Li_20); }
            xma148_25_25_3_0[Li_12] = Ld_0 / xma148_25_25_3_N;
           }
         else
           {
            Ld_0 = 0;
            for(Li_20 = Li_12 + (xma148_25_25_3_N - 1) / 2; Li_20 >= 0; Li_20--)
              { if(Li_20>=rates_total) continue; Ld_0 += PriceShift(xma148_25_25_3_mode, Li_20); }
            xma148_25_25_3_0[Li_12] = (Ld_0 + Ld_0 * ((xma148_25_25_3_N - 1) / 2 - Li_12) / ((xma148_25_25_3_N - 1) / 2 + Li_12 + 1)) / xma148_25_25_3_N;
           }
        //    WriteLog("Time=" + TimeToString(iTime(Symbol(),Period(),Li_12), TIME_DATE|TIME_MINUTES|TIME_SECONDS) + 
        // ",Bar " + IntegerToString(Li_12) + ",xma148_25_25_3_0: " + DoubleToString(xma148_25_25_3_0[Li_12]) +
        // "  Low data: " + DoubleToString(f0_0(Li_20, xma148_25_25_3_mode), 4));
        }
      for(Li_12 = limitXma_25_25_3; Li_12 >= 0; Li_12--)
        {
         if(Li_12 >= (xma148_25_25_3_N1 - 1) / 2)
           {
            Ld_0 = 0;
            for(Li_20 = Li_12 + (xma148_25_25_3_N1 - 1) / 2; Li_20 >= Li_12 - (xma148_25_25_3_N1 - 1) / 2; Li_20--)
              { if(Li_20>=rates_total) continue; Ld_0 += xma148_25_25_3_0[Li_20]; }
            xma148_25_25_3_1[Li_12] = Ld_0 / xma148_25_25_3_N1;
           }
         else
           {
            Ld_0 = 0;
            for(Li_20 = Li_12 + (xma148_25_25_3_N1 - 1) / 2; Li_20 >= 0; Li_20--)
              { if(Li_20>=rates_total) continue; Ld_0 += xma148_25_25_3_0[Li_20]; }
            xma148_25_25_3_1[Li_12] = (Ld_0 + Ld_0 * ((xma148_25_25_3_N1 - 1) / 2 - Li_12) / ((xma148_25_25_3_N1 - 1) / 2 + Li_12 + 1)) / xma148_25_25_3_N1;
           }
        }
      //
      for(Li_12 = limitXma_25_25_2; Li_12 >= 0; Li_12--)
        {
         if(Li_12 >= (xma148_25_25_2_N - 1) / 2)
           {
            Ld_0 = 0;
            for(Li_20 = Li_12 + int((xma148_25_25_2_N - 1) / 2) ; Li_20 >= Li_12 - (xma148_25_25_2_N - 1) / 2; Li_20--)
              { if(Li_20>=rates_total) continue; Ld_0 += PriceShift( xma148_25_25_2_mode,Li_20); }
            xma148_25_25_2_0[Li_12] = Ld_0 / xma148_25_25_2_N;
           }
         else
           {
            Ld_0 = 0;
            for(Li_20 = Li_12 + (xma148_25_25_2_N - 1) / 2; Li_20 >= 0; Li_20--)
              { if(Li_20>=rates_total) continue; Ld_0 += PriceShift(xma148_25_25_2_mode,Li_20); }
            xma148_25_25_2_0[Li_12] = (Ld_0 + Ld_0 * ((xma148_25_25_2_N - 1) / 2 - Li_12) / ((xma148_25_25_2_N - 1) / 2 + Li_12 + 1)) / xma148_25_25_2_N;
           }
        }
      for(Li_12 = limitXma_25_25_2; Li_12 >= 0; Li_12--)
        {
         if(Li_12 >= (xma148_25_25_2_N1 - 1) / 2)
           {
            Ld_0 = 0;
            for(Li_20 = Li_12 + (xma148_25_25_2_N1 - 1) / 2; Li_20 >= Li_12 - (xma148_25_25_2_N1 - 1) / 2; Li_20--)
              { if(Li_20>=rates_total) continue; Ld_0 += xma148_25_25_2_0[Li_20]; }
            xma148_25_25_2_1[Li_12] = Ld_0 / xma148_25_25_2_N1;
           }
         else
           {
            Ld_0 = 0;
            for(Li_20 = Li_12 + (xma148_25_25_2_N1 - 1) / 2; Li_20 >= 0; Li_20--)
              { if(Li_20>=rates_total) continue; Ld_0 += xma148_25_25_2_0[Li_20]; }
            xma148_25_25_2_1[Li_12] = (Ld_0 + Ld_0 * ((xma148_25_25_2_N1 - 1) / 2 - Li_12) / ((xma148_25_25_2_N1 - 1) / 2 + Li_12 + 1)) / xma148_25_25_2_N1;
           }
        }
      ///MHDMT_ZT
      for(li_48 = limit-1; li_48 >=0; li_48--)
        {
         li_16 = false;
         li_20 = false;
         //WriteLog("Time=" + TimeToString(iTime(Symbol(),Period(),li_48), TIME_DATE|TIME_MINUTES|TIME_SECONDS) + 
         //",Bar " + IntegerToString(li_48) + ", pinghua xma148_25_25_3_1: " + DoubleToString(xma148_25_25_3_1[li_48]) + ",xma148_25_25_2_1: " + DoubleToString(xma148_25_25_2_1[li_48]));
         g_ibuf_116[li_48] = 2.0 * xma148_25_25_3_1[li_48] - xma148_25_25_2_1[li_48];
         g_ibuf_120[li_48] = 2.0 * xma148_25_25_2_1[li_48] - xma148_25_25_3_1[li_48];
         g_ibuf_124[li_48] = 3.9 * (xma148_25_25_2_1[li_48] - xma148_25_25_3_1[li_48]) + xma148_25_25_2_1[li_48];
         g_ibuf_128[li_48] = xma148_25_25_3_1[li_48] - 3.9 * (xma148_25_25_2_1[li_48] - xma148_25_25_3_1[li_48]);
         g_ibuf_132[li_48] = belt156_2[li_48];
         g_ibuf_136[li_48] = belt156_3[li_48];
         slld_0[li_48] = belt156_2[li_48] + 2.0 * belt156_4[li_48];
         slld_8[li_48] = belt156_3[li_48] - 2.0 * belt156_4[li_48]; //if(li_48==0) Print(slld_0[li_48]," ",slld_8[li_48]);
         DrawTLineSp(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"Graybelt",
                     PriceShift(4,li_48),g_ibuf_132[li_48],
                     PriceShift(4,li_48),g_ibuf_136[li_48],
                     BeltColor,STYLE_SOLID,g_width_112,false,true);
         if(g_ibuf_120[li_48] > slld_0[li_48] && g_ibuf_116[li_48] > slld_8[li_48])
           {
            DrawTLineSp(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"duo",
                        PriceShift(4,li_48),g_ibuf_116[li_48],
                        PriceShift(4,li_48),g_ibuf_120[li_48],
                        UpTrendChannelColor,STYLE_SOLID,g_width_112,false,true);
           }
         else
           {
            ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"duo");
           }
         if(g_ibuf_120[li_48] < slld_0[li_48] && g_ibuf_116[li_48] < slld_8[li_48])
           {
            DrawTLineSp(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"dong",
                        PriceShift(4,li_48),g_ibuf_120[li_48],
                        PriceShift(4,li_48),g_ibuf_116[li_48],
                        DownTrendChannelColor,STYLE_SOLID,g_width_112,false,true);
           }
         else
           {
            ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"dong");
           }
         if(g_ibuf_120[li_48] < slld_0[li_48] && g_ibuf_116[li_48] > slld_8[li_48])
           {
            DrawTLineSp(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"dang",
                        PriceShift(4,li_48),g_ibuf_116[li_48],
                        PriceShift(4,li_48),g_ibuf_120[li_48],
                        SideWayChannelColor,STYLE_SOLID,g_width_112,false,true);
           }
         else
           {
            ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"dang");
           }
         if(g_ibuf_116[li_48+1] < PriceShift(3,li_48+1) && g_ibuf_116[li_48] > PriceShift(3,li_48) &&
            ((g_ibuf_120[li_48] > slld_0[li_48] && g_ibuf_116[li_48] > slld_8[li_48]) || (g_ibuf_120[li_48] < slld_0[li_48] &&
                  g_ibuf_116[li_48] > slld_8[li_48])))
           {
               string msg =
        "BUY | Time=" + TimeToString(PriceShift(4,li_48), TIME_DATE|TIME_MINUTES|TIME_SECONDS) +
        ", g116_0=" + DoubleToString(g_ibuf_116[li_48], 6) +
        ", g116_1=" + DoubleToString(g_ibuf_116[li_48+1], 6) +
        ", g120_0=" + DoubleToString(g_ibuf_120[li_48], 6) +
        ", g120_1=" + DoubleToString(g_ibuf_120[li_48+1], 6) +
        ", slld0_0=" + DoubleToString(slld_0[li_48], 6) +
        ", slld8_0=" + DoubleToString(slld_8[li_48], 6) +
        ", low_0="   + DoubleToString(PriceShift(3,li_48), 6) +
        ", low_1="   + DoubleToString(PriceShift(3,li_48+1), 6) +
        ", high_0="  + DoubleToString(PriceShift(2,li_48), 6) +
        ", high_1="  + DoubleToString(PriceShift(2,li_48+1), 6);

    WriteLog(msg);
           
           
           
           
            SetText(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"duosong",0,
                    PriceShift(4,li_48),g_ibuf_128[li_48],
                    ((!isChs)?"SL-BUY":"duosong"),strFt,fsx-2,SL_BUY_TextColor,0,ANCHOR_UPPER);
            SetText(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"zuoduo",0,
                    PriceShift(4,li_48),PriceShift(3,li_48),
                    ((!isChs)?"BUY":"zuoduo"),strFt,fsx,BUY_TextColor,0,ANCHOR_UPPER);
            li_16 = true;
           }
         else
           {
            ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"duosong");
            ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"zuoduo");
           }
         if(PriceShift(2,li_48 + 1) < g_ibuf_120[li_48 + 1] && PriceShift(2,li_48) > g_ibuf_120[li_48] &&
            ((g_ibuf_120[li_48] < slld_0[li_48] && g_ibuf_116[li_48] < slld_8[li_48]) || (g_ibuf_120[li_48] < slld_0[li_48] &&
                  g_ibuf_116[li_48] > slld_8[li_48])))
           {
           string msg =
        "SELL | Time=" + TimeToString(PriceShift(4,li_48), TIME_DATE|TIME_MINUTES|TIME_SECONDS) +
        ", g116_0=" + DoubleToString(g_ibuf_116[li_48], 6) +
        ", g116_1=" + DoubleToString(g_ibuf_116[li_48+1], 6) +
        ", g120_0=" + DoubleToString(g_ibuf_120[li_48], 6) +
        ", g120_1=" + DoubleToString(g_ibuf_120[li_48+1], 6) +
        ", slld0_0=" + DoubleToString(slld_0[li_48], 6) +
        ", slld8_0=" + DoubleToString(slld_8[li_48], 6) +
        ", low_0="   + DoubleToString(PriceShift(3,li_48), 6) +
        ", low_1="   + DoubleToString(PriceShift(3,li_48+1), 6) +
        ", high_0="  + DoubleToString(PriceShift(2,li_48), 6) +
        ", high_1="  + DoubleToString(PriceShift(2,li_48+1), 6);

    WriteLog(msg);
            SetText(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"kongsong",0,
                    PriceShift(4,li_48),g_ibuf_124[li_48],
                    ((!isChs)?"SL-SELL":"kongsong"),strFt,fsx-2,SL_SELL_TextColor,0,ANCHOR_UPPER);
            SetText(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"zuokong",0,
                    PriceShift(4,li_48),PriceShift(2,li_48),
                    ((!isChs)?"SELL":"kong"),strFt,fsx,SELL_TextColor,0,ANCHOR_LOWER);
            li_20 = true;
           }
         else
           {
            ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"kongsong");
            ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"zuokong");
           }
         if(g_ibuf_116[li_48 + 1] < PriceShift(3,li_48 + 1) && g_ibuf_116[li_48] > PriceShift(3,li_48) &&
            ((g_ibuf_120[li_48] < slld_0[li_48] && g_ibuf_116[li_48] < slld_8[li_48]) ||
             !(g_ibuf_120[li_48] < slld_0[li_48] && g_ibuf_116[li_48] > slld_8[li_48])) && !li_16)
           {
           string msg =
        "CLOSE-SELL | Time=" + TimeToString(PriceShift(4,li_48), TIME_DATE|TIME_MINUTES|TIME_SECONDS) +
        ", g116_0=" + DoubleToString(g_ibuf_116[li_48], 6) +
        ", g116_1=" + DoubleToString(g_ibuf_116[li_48+1], 6) +
        ", g120_0=" + DoubleToString(g_ibuf_120[li_48], 6) +
        ", g120_1=" + DoubleToString(g_ibuf_120[li_48+1], 6) +
        ", slld0_0=" + DoubleToString(slld_0[li_48], 6) +
        ", slld8_0=" + DoubleToString(slld_8[li_48], 6) +
        ", low_0="   + DoubleToString(PriceShift(3,li_48), 6) +
        ", low_1="   + DoubleToString(PriceShift(3,li_48+1), 6) +
        ", high_0="  + DoubleToString(PriceShift(2,li_48), 6) +
        ", high_1="  + DoubleToString(PriceShift(2,li_48+1), 6);

    WriteLog(msg);
            SetText(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"kongping",0,
                    PriceShift(4,li_48),PriceShift(3,li_48),
                    ((!isChs)?"CLOSE-SELL":"kongping"),strFt,fsx-2,CLOSE_SELL_TextColor,0,ANCHOR_UPPER);
           }
         else
           {
            ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"kongping");
           }
         if(PriceShift(2,li_48 + 1) < g_ibuf_120[li_48 + 1] && PriceShift(2,li_48) > g_ibuf_120[li_48] &&
            ((g_ibuf_120[li_48] > slld_0[li_48] && g_ibuf_116[li_48] > slld_8[li_48]) ||
             !(g_ibuf_120[li_48] < slld_0[li_48] && g_ibuf_116[li_48] > slld_8[li_48])) && !li_20)
           {
           string msg =
        "CLOSE-BUY | Time=" + TimeToString(PriceShift(4,li_48), TIME_DATE|TIME_MINUTES|TIME_SECONDS) +
        ", g116_0=" + DoubleToString(g_ibuf_116[li_48], 6) +
        ", g116_1=" + DoubleToString(g_ibuf_116[li_48+1], 6) +
        ", g120_0=" + DoubleToString(g_ibuf_120[li_48], 6) +
        ", g120_1=" + DoubleToString(g_ibuf_120[li_48+1], 6) +
        ", slld0_0=" + DoubleToString(slld_0[li_48], 6) +
        ", slld8_0=" + DoubleToString(slld_8[li_48], 6) +
        ", low_0="   + DoubleToString(PriceShift(3,li_48), 6) +
        ", low_1="   + DoubleToString(PriceShift(3,li_48+1), 6) +
        ", high_0="  + DoubleToString(PriceShift(2,li_48), 6) +
        ", high_1="  + DoubleToString(PriceShift(2,li_48+1), 6);

    WriteLog(msg);
            SetText(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"duoping",0,
                    PriceShift(4,li_48),PriceShift(2,li_48),
                    ((!isChs)?"CLOSE-BUY":"??"),strFt,fsx-2,CLOSE_BUY_TextColor,0,ANCHOR_LOWER);
           }
         else
           {
            ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"duoping");
           }
        }
     }
   indC++;
   dtInd=PriceShift(4,0);
///for mql5 market
   if(ArraySize(g_ibuf_116)<5)
      return;
   li_48=0;
   li_16=false;
   li_20=false;
   if(g_ibuf_116[li_48+1] < PriceShift(3,li_48+1) && g_ibuf_116[li_48] > PriceShift(3,li_48) &&
      ((g_ibuf_120[li_48] > slld_0[li_48] && g_ibuf_116[li_48] > slld_8[li_48]) || (g_ibuf_120[li_48] < slld_0[li_48] &&
            g_ibuf_116[li_48] > slld_8[li_48])))
     {

    



      SetText(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"duosong",0,
              PriceShift(4,li_48),g_ibuf_128[li_48],
              ((!isChs)?"SL-BUY":"duosong"),strFt,fsx-2,SL_BUY_TextColor,0,ANCHOR_UPPER);
      SetText(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"zuoduo",0,
              PriceShift(4,li_48),PriceShift(3,li_48),
              ((!isChs)?"BUY":"zuoduo"),strFt,fsx,BUY_TextColor,0,ANCHOR_UPPER);
      li_16 = true;
     }
   else
     {
      ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"duosong");
      ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"zuoduo");
     }
   if(PriceShift(2,li_48 + 1) < g_ibuf_120[li_48 + 1] && PriceShift(2,li_48) > g_ibuf_120[li_48] &&
      ((g_ibuf_120[li_48] < slld_0[li_48] && g_ibuf_116[li_48] < slld_8[li_48]) || (g_ibuf_120[li_48] < slld_0[li_48] &&
            g_ibuf_116[li_48] > slld_8[li_48])))
     {
      SetText(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"kongsong",0,
              PriceShift(4,li_48),g_ibuf_124[li_48],
              ((!isChs)?"SL-SELL":"kongsong"),strFt,fsx-2,SL_SELL_TextColor,0,ANCHOR_UPPER);
      SetText(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"zuokong",0,
              PriceShift(4,li_48),PriceShift(2,li_48),
              ((!isChs)?"SELL":"zuokong"),strFt,fsx,SELL_TextColor,0,ANCHOR_LOWER);
      li_20 = true;
     }
   else
     {
      ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"kongsong");
      ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"zuokong");
     }
   if(g_ibuf_116[li_48 + 1] < PriceShift(3,li_48 + 1) && g_ibuf_116[li_48] > PriceShift(3,li_48) &&
      ((g_ibuf_120[li_48] < slld_0[li_48] && g_ibuf_116[li_48] < slld_8[li_48]) ||
       !(g_ibuf_120[li_48] < slld_0[li_48] && g_ibuf_116[li_48] > slld_8[li_48])) && !li_16)
     {
      SetText(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"kongping",0,
              PriceShift(4,li_48),PriceShift(3,li_48),
              ((!isChs)?"CLOSE-SELL":"kongping"),strFt,fsx-2,CLOSE_SELL_TextColor,0,ANCHOR_UPPER);
     }
   else
     {
      ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"kongping");
     }
   if(PriceShift(2,li_48 + 1) < g_ibuf_120[li_48 + 1] && PriceShift(2,li_48) > g_ibuf_120[li_48] &&
      ((g_ibuf_120[li_48] > slld_0[li_48] && g_ibuf_116[li_48] > slld_8[li_48]) ||
       !(g_ibuf_120[li_48] < slld_0[li_48] && g_ibuf_116[li_48] > slld_8[li_48])) && !li_20)
     {
      SetText(strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"duoping",0,
              PriceShift(4,li_48),PriceShift(2,li_48),
              ((!isChs)?"CLOSE-BUY":"duoping"),strFt,fsx-2,CLOSE_BUY_TextColor,0,ANCHOR_LOWER);
     }
   else
     {
      ObjectDelete(0,strEA+"TL_"+IntegerToString(PriceShift(4,li_48))+"duoping");
     }
///
   if(PopupAlert==A || SoundAlert==A || MailAlert==A || MobileAlert==A)
     {
      if(PriceShift(4,0)-dtAlertBuy>=kNoAlert*PeriodSeconds(Period()) &&
         ObjectFind(0,strEA+"TL_"+IntegerToString(PriceShift(4,0))+"zuoduo")!=-1)
        {
         dtAlertBuy=PriceShift(4,0);
         AlertMessage(Symbol()+"_"+PeriodToString(Period())+
                      ((!isChs)?" BUY SIGNAL from Dragon Channel":
                       " BUY SIGNAL - Dragon Channel"));
        }
      if(PriceShift(4,0)-dtAlertSell>=kNoAlert*PeriodSeconds(Period()) &&
         ObjectFind(0,strEA+"TL_"+IntegerToString(PriceShift(4,0))+"zuokong")!=-1)
        {
         dtAlertSell=PriceShift(4,0);
         AlertMessage(Symbol()+"_"+PeriodToString(Period())+
                      ((!isChs)?" SELL SIGNAL from Dragon Channel":
                       " SELL SIGNAL - Dragon Channel"));
        }
      if(PriceShift(4,0)-dtAlertCloseBuy>=kNoAlert*PeriodSeconds(Period()) &&
         ObjectFind(0,strEA+"TL_"+IntegerToString(PriceShift(4,0))+"duoping")!=-1)
        {
         dtAlertCloseBuy=PriceShift(4,0);
         AlertMessage(Symbol()+"_"+PeriodToString(Period())+
                      ((!isChs)?" CLOSE-BUY SIGNAL from Dragon Channel":
                       " CLOSE-BUY - Dragon Channel"));
        }
      if(PriceShift(4,0)-dtAlertCloseSell>=kNoAlert*PeriodSeconds(Period()) &&
         ObjectFind(0,strEA+"TL_"+IntegerToString(PriceShift(4,0))+"kongping")!=-1)
        {
         dtAlertCloseSell=PriceShift(4,0);
         AlertMessage(Symbol()+"_"+PeriodToString(Period())+
                      ((!isChs)?" CLOSE-SELL SIGNAL from Dragon Channel":
                       " ???? - ??????"));
        }
     }
///
   ChartRedraw();
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
double f0_0(int Ai_0, int Ai_4)
  {
   double Ld_ret_8 = 0;
   switch(Ai_4)
     {
      case 0:
         Ld_ret_8 = iOpen(Symbol(),Period(),Ai_0);
         break;
      case 1:
         Ld_ret_8 = iClose(Symbol(),Period(),Ai_0);
         break;
      case 2:
         Ld_ret_8 = iHigh(Symbol(),Period(),Ai_0);
         break;
      case 3:
         Ld_ret_8 = iLow(Symbol(),Period(),Ai_0);
     }
   return (Ld_ret_8);
  }
  
// 封装带 Shift 偏移的价格读取

double PriceShift(int mode, int shift_bar)

{

   int idx = shift_bar + Shift; // 实际读取位置 = 原始索引 + 偏移


   switch(mode)

   {

      case 0:   return iOpen(Symbol(), Period(), idx);

      case 2:   return iHigh(Symbol(), Period(), idx);

      case 3:    return iLow(Symbol(), Period(), idx);

      case 1:  return iClose(Symbol(), Period(), idx);

      case 4:   return (double)iTime(Symbol(), Period(), idx);

   }

   return 0;

}  

//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void IndicatorIni()
  {
   IndicatorBuffers(17);
   //SetIndexStyle(0,DRAW_LINE,EMPTY,EMPTY,Line1Color);
   SetIndexBuffer(0,g_ibuf_116);
   SetIndexStyle(0,DRAW_NONE);
   //SetIndexStyle(1,DRAW_LINE,EMPTY,EMPTY,Line2Color);
   SetIndexBuffer(1,g_ibuf_120);
   SetIndexStyle(1,DRAW_NONE);
   //SetIndexStyle(2,DRAW_LINE,EMPTY,EMPTY,Line3Color);
   SetIndexBuffer(2,g_ibuf_124);
   SetIndexStyle(2,DRAW_NONE);
   //SetIndexStyle(3,DRAW_LINE,EMPTY,EMPTY,Line4Color);
   SetIndexBuffer(3,g_ibuf_128);
   SetIndexStyle(3,DRAW_NONE);
   //SetIndexStyle(4,DRAW_LINE,EMPTY,EMPTY,Line5Color);
   SetIndexBuffer(4,g_ibuf_132);
   SetIndexStyle(4,DRAW_NONE);
   //SetIndexStyle(5,DRAW_LINE,EMPTY,EMPTY,Line6Color);
   SetIndexBuffer(5,g_ibuf_136);
   SetIndexStyle(5,DRAW_NONE);
   SetIndexBuffer(6,xma148_25_25_2_0);
   SetIndexStyle(6,DRAW_NONE);
   SetIndexBuffer(7,xma148_25_25_3_0);
   SetIndexStyle(7,DRAW_NONE);
   SetIndexBuffer(8,xma148_25_25_2_1);
   SetIndexStyle(8,DRAW_NONE);
   SetIndexBuffer(9,xma148_25_25_3_1);
   SetIndexStyle(9,DRAW_NONE);
   SetIndexBuffer(10,belt156_0);
   SetIndexStyle(10,DRAW_NONE);
   SetIndexBuffer(11,belt156_1);
   SetIndexStyle(11,DRAW_NONE);
   SetIndexBuffer(12,belt156_2);
   SetIndexStyle(12,DRAW_NONE);
   SetIndexBuffer(13,belt156_3);
   SetIndexStyle(13,DRAW_NONE);
   SetIndexBuffer(14,belt156_4);
   SetIndexStyle(14,DRAW_NONE);
   SetIndexBuffer(15,slld_0);
   SetIndexStyle(15,DRAW_NONE);
   SetIndexBuffer(16,slld_8);
   SetIndexStyle(16,DRAW_NONE);
   iBarMax=nBarMax;
   ArrayIni();
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void ArrayIni(bool noObjPurge=false)
  {
   double iniValue=0;
   ArraySetAsSeries(g_ibuf_116,true);
   ArrayInitialize(g_ibuf_116,iniValue);
   ArraySetAsSeries(g_ibuf_120,true);
   ArrayInitialize(g_ibuf_120,iniValue);
   ArraySetAsSeries(g_ibuf_124,true);
   ArrayInitialize(g_ibuf_124,iniValue);
   ArraySetAsSeries(g_ibuf_128,true);
   ArrayInitialize(g_ibuf_128,iniValue);
   ArraySetAsSeries(g_ibuf_132,true);
   ArrayInitialize(g_ibuf_132,iniValue);
   ArraySetAsSeries(g_ibuf_136,true);
   ArrayInitialize(g_ibuf_136,iniValue);
   ArraySetAsSeries(xma148_25_25_2_0,true);
   ArrayInitialize(xma148_25_25_2_0,iniValue);
   ArraySetAsSeries(xma148_25_25_3_0,true);
   ArrayInitialize(xma148_25_25_3_0,iniValue);
   ArraySetAsSeries(xma148_25_25_2_1,true);
   ArrayInitialize(xma148_25_25_2_1,iniValue);
   ArraySetAsSeries(xma148_25_25_3_1,true);
   ArrayInitialize(xma148_25_25_3_1,iniValue);
   ArraySetAsSeries(belt156_0,true);
   ArrayInitialize(belt156_0,iniValue);
   ArraySetAsSeries(belt156_1,true);
   ArrayInitialize(belt156_1,iniValue);
   ArraySetAsSeries(belt156_2,true);
   ArrayInitialize(belt156_2,iniValue);
   ArraySetAsSeries(belt156_3,true);
   ArrayInitialize(belt156_3,iniValue);
   ArraySetAsSeries(belt156_4,true);
   ArrayInitialize(belt156_4,iniValue);
   ArraySetAsSeries(slld_0,true);
   ArrayInitialize(slld_0,iniValue);
   ArraySetAsSeries(slld_8,true);
   ArrayInitialize(slld_8,iniValue);
   if(!noObjPurge)
      ObjectsDeleteAll(0,strEA+"TL_");
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
bool CheckIniError()
  {
   isChs=false;
   strFt=!isChs?strFte:strFth;
   fsx=!isChs?fse:fsc;
   bError=false;
   return(false);
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void SetLabel(string nm,string tx,int xd,int yd,string fn,int fs,color ct,
              ENUM_BASE_CORNER cn=CORNER_LEFT_UPPER,ENUM_ANCHOR_POINT ap=ANCHOR_LEFT_UPPER)
  {
   if(ObjectFind(0,nm)<0)
      ObjectCreate(0,nm,OBJ_LABEL,0,0,0);
   ObjectSetInteger(0,nm,OBJPROP_STYLE,STYLE_SOLID);
   ObjectSetString(0,nm,OBJPROP_TOOLTIP,"\n");
   ObjectSetInteger(0,nm,OBJPROP_XDISTANCE,xd);
   ObjectSetInteger(0,nm,OBJPROP_YDISTANCE,yd);
   ObjectSetInteger(0,nm,OBJPROP_COLOR,ct);
   ObjectSetString(0,nm,OBJPROP_TEXT,tx);
   ObjectSetString(0,nm,OBJPROP_FONT,fn);
   ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,fs);
   ObjectSetInteger(0,nm,OBJPROP_CORNER,cn);
   ObjectSetInteger(0,nm,OBJPROP_ANCHOR,ap);
   ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0,nm,OBJPROP_SELECTED,false);
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void DrawTLineSp(string strTlObject,datetime dTime1,double dPrice1,datetime dTime2,double dPrice2,
                 color cr,ENUM_LINE_STYLE lnStyle,int iWidth,bool bRaylight,bool bBack)
  {
   if(ObjectFind(0,strTlObject)<0)
      ObjectCreate(0,strTlObject,OBJ_TREND,0,dTime1,dPrice1,dTime2,dPrice2);
   ObjectSetDouble(0,strTlObject,OBJPROP_PRICE,0,dPrice1);
   ObjectSetInteger(0,strTlObject,OBJPROP_TIME,0,dTime1);
   ObjectSetDouble(0,strTlObject,OBJPROP_PRICE,1,dPrice2);
   ObjectSetInteger(0,strTlObject,OBJPROP_TIME,1,dTime2);
   ObjectSetInteger(0,strTlObject,OBJPROP_STYLE,lnStyle);
   ObjectSetInteger(0,strTlObject,OBJPROP_COLOR,cr);
   ObjectSetInteger(0,strTlObject,OBJPROP_WIDTH,iWidth);
   ObjectSetInteger(0,strTlObject,OBJPROP_RAY_RIGHT,bRaylight);
   ObjectSetInteger(0,strTlObject,OBJPROP_BACK,bBack);
   ObjectSetString(0,strTlObject,OBJPROP_TOOLTIP,"\n");
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void SetText(string nm,int ct,datetime tm,double pc,string tx,string fn,int fs,color cr,double ag,ENUM_ANCHOR_POINT ach)
  {
   if(ObjectFind(0,nm)<0)
      ObjectCreate(ct,nm,OBJ_TEXT,0,tm,pc);
   ObjectSetString(ct,nm,OBJPROP_TEXT,tx);
   ObjectSetString(0,nm,OBJPROP_TOOLTIP,"\n");
   ObjectSetDouble(ct,nm,OBJPROP_PRICE,0,pc);
   ObjectSetInteger(ct,nm,OBJPROP_TIME,0,tm);
   ObjectSetString(ct,nm,OBJPROP_FONT,fn);
   ObjectSetInteger(ct,nm,OBJPROP_FONTSIZE,fs);
   ObjectSetDouble(ct,nm,OBJPROP_ANGLE,ag);
   ObjectSetInteger(ct,nm,OBJPROP_ANCHOR,ach);
   ObjectSetInteger(ct,nm,OBJPROP_COLOR,cr);
   ObjectSetInteger(ct,nm,OBJPROP_BACK,false);
   ObjectSetInteger(ct,nm,OBJPROP_SELECTABLE,false);
   ObjectSetInteger(ct,nm,OBJPROP_SELECTED,false);
   ObjectSetInteger(ct,nm,OBJPROP_HIDDEN,false);
   ObjectSetInteger(ct,nm,OBJPROP_ZORDER,0);
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void AlertMessage(string strInput)
  {
   if(PopupAlert==A)
      Alert(strInput);
   if(SoundAlert==A)
      PlaySound("alert.wav");
   if(MailAlert==A)
      SendMail(strInput,"GMT time: "+TimeToString(TimeGMT(),TIME_DATE|TIME_MINUTES|TIME_SECONDS));
   if(MobileAlert==A)
      SendNotification(strInput);
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
string PeriodToString(int imin)
  {
   string strprd="";
   if(imin==0 || imin==(int)PERIOD_CURRENT)
      imin=Period();
   switch(imin)
     {
      case(PERIOD_M1):
         strprd="M1";
         break;
      case(PERIOD_M5):
         strprd="M5";
         break;
      case(PERIOD_M15):
         strprd="M15";
         break;
      case(PERIOD_M30):
         strprd="M30";
         break;
      case(PERIOD_H1):
         strprd="H1";
         break;
      case(PERIOD_H4):
         strprd="H4";
         break;
      case(PERIOD_D1):
         strprd="D1";
         break;
      case(PERIOD_W1):
         strprd="W1";
         break;
      case(PERIOD_MN1):
         strprd="MN1";
         break;
     }
   return(strprd);
  }
//+------------------------------------------------------------------+
//|                                                                  |
//+------------------------------------------------------------------+
void ParamStored(int iMode,int iReason)
  {
   if(iMode==1)
     {
      if(GlobalVariableCheck("dtAlertBuy"+IntegerToString(ChartID())))
         dtAlertBuy=(datetime)GlobalVariableGet("dtAlertBuy"+IntegerToString(ChartID()));
      if(GlobalVariableCheck("dtAlertSell"+IntegerToString(ChartID())))
         dtAlertSell=(datetime)GlobalVariableGet("dtAlertSell"+IntegerToString(ChartID()));
      if(GlobalVariableCheck("dtAlertCloseBuy"+IntegerToString(ChartID())))
         dtAlertCloseBuy=(datetime)GlobalVariableGet("dtAlertCloseBuy"+IntegerToString(ChartID()));
      if(GlobalVariableCheck("dtAlertCloseSell"+IntegerToString(ChartID())))
         dtAlertCloseSell=(datetime)GlobalVariableGet("dtAlertCloseSell"+IntegerToString(ChartID()));
     }
   if(iMode==2)
     {
      if(iReason==REASON_RECOMPILE || iReason==REASON_CHARTCHANGE || iReason==REASON_PARAMETERS || iReason==REASON_TEMPLATE)// || iReason==REASON_CLOSE)
        {
         GlobalVariableSet("dtAlertBuy"+IntegerToString(ChartID()),(double)dtAlertBuy);
         GlobalVariableSet("dtAlertSell"+IntegerToString(ChartID()),(double)dtAlertSell);
         GlobalVariableSet("dtAlertCloseBuy"+IntegerToString(ChartID()),(double)dtAlertCloseBuy);
         GlobalVariableSet("dtAlertCloseSell"+IntegerToString(ChartID()),(double)dtAlertCloseSell);
        }
      else
        {
         for(int ii=GlobalVariablesTotal()-1; ii>=0; ii--)
            if(StringFind(GlobalVariableName(ii),IntegerToString(ChartID()),0)!=-1)
               GlobalVariableDel(GlobalVariableName(ii));
        }
     }
  }
//+------------------------------------------------------------------+
