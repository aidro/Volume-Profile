def VolumeProfile(dataframe: list, Interval: str, Asset: str, RangeStart: str, RangeEnd: str, *args):
    """
    Perform volume profile analysis over a specified date range to identify key price levels.

    This function calculates the volume profile of an asset over a specified time range (`RangeStart` to `RangeEnd`) 
    for a given time interval. It divides the price range into 240 price buckets and assigns volume to each bucket 
    based on the historical price data. Key levels such as the Point of Control (POC), Value Area High (VAH), and 
    Value Area Low (VAL) are calculated based on volume distribution. If "VP" is provided in `args`, the function 
    will also return the heatmap of volume levels.

    Args:
        dataframe (list): A list of DataFrames containing candlestick data for different intervals.
        Interval (str): The time interval for the data (e.g., "1M", "5M").
        Asset (str): The asset symbol being analyzed.
        RangeStart (str): The start date of the range for analysis.
        RangeEnd (str): The end date of the range for analysis.
        *args: Optional arguments, such as "VP" for volume profile heatmap.

    Returns:
        tuple: A tuple containing:
            - POC (float): The Point of Control (price level with the highest volume).
            - VAH (float): The Value Area High (price level marking the upper boundary of 70% of the volume).
            - VAL (float): The Value Area Low (price level marking the lower boundary of 70% of the volume).
            - list: The bucket with the highest volume (either HIGH, MID, or LOW).
    """
    ConversionTable = ["1M", "3M", "5M", "15M", "60M"]
    RangeStartiso = int(datetime.strptime(RangeStart, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
    RangeEndiso = int(datetime.strptime(RangeEnd, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
    
    for x in ConversionTable[:ConversionTable.index(Interval)+1]:
        if int((RangeEndiso-RangeStartiso) / (int(x[:-1]) * 60)) <= 5000:
            if x == "3M":
                start_insert = str(int(RangeStart[-5:-3]) - int(RangeStart[-5:-3]) % 3)
                end_insert = str(int(RangeEnd[-5:-3]) - int(RangeEnd[-5:-3]) % 3)

                if len(start_insert) != 2:
                    start_insert = "0" + start_insert
                
                if len(end_insert) != 2:
                    end_insert = "0" + end_insert

                if int(RangeStart[-5:-3]) % 3 != 0:
                    RangeStart = RangeStart[:-5] + start_insert + ":00"
                
                else:
                    RangeStart = RangeStart

                if int(RangeEnd[-5:-3]) % 3 != 0:
                    RangeEnd = RangeEnd[:-5] + end_insert + ":00"
                
                else:
                    RangeEnd = RangeEnd

                df = dataframe[ConversionTable.index(x)]
                if RangeStart not in set(df.date) or RangeEnd not in set(df.date):
                    df = ExpandDataFrame(df, x[:-1], Asset, RangeStart)

                df = df.iloc[df.loc[df.date == RangeStart].index[0]:(df.loc[df.date == RangeEnd].index[0]+1)]
            else:
                df = dataframe[ConversionTable.index(x)]
                if RangeStart not in set(df.date) or RangeEnd not in set(df.date):
                    df = ExpandDataFrame(df, x[:-1], Asset, RangeStart)
                
                df = df.iloc[df.loc[df.date == RangeStart].index[0]:(df.loc[df.date == RangeEnd].index[0]+int(Interval[:-1]))]
            break

        else:
            continue

    highest = df.high.max()
    lowest = df.low.min()

    pricestep = (highest-lowest)/240
    canvas = [0 for _ in range(240)]

    for row in df.itertuples():
        start_iloc = floor(round((highest - row.high) / pricestep, 2))
        end_iloc = ceil(round((highest - row.low) / pricestep, 2))-1

        start_perc = 100 - (highest - (start_iloc*pricestep) - row.high)/pricestep *100
        end_perc = (highest - (end_iloc*pricestep) - row.low)/pricestep *100

        for x in range(start_iloc, end_iloc+1):
            if start_iloc - end_iloc < 1:
                if x == start_iloc:
                    canvas[x] += ((row.volume/((end_iloc+1)-start_iloc))/100) * start_perc
                    continue
                
                if x == end_iloc:
                    canvas[x] += ((row.volume/((end_iloc+1)-start_iloc))/100) * end_perc
                    continue

            canvas[x] += row.volume/((end_iloc+1)-start_iloc)

    POC = ((highest - (pricestep * (canvas.index(max(canvas)))) + highest - (pricestep * (canvas.index(max(canvas))+1))))/2

    Canvas_Volume = sum(canvas) * 0.7
    Value_Area_Volume = 0
    Value_Area = [[0, 0] for _ in range(240)]
    Move_Up = [True, 0]
    Move_Down = [True, 0]
    
    for x in range(0, len(canvas)):
        if Value_Area_Volume >= Canvas_Volume:
            break
        
        if Move_Up[0]:
            up_one = (canvas.index(max(canvas))-(2*Move_Up[1]+1))
            up_two = (canvas.index(max(canvas))-(2*Move_Up[1]+2))

            if up_two <= 0:
                up_two = up_one
        
        if Move_Down[0]:
            down_one = (canvas.index(max(canvas))+(2*Move_Down[1]+1))
            down_two = (canvas.index(max(canvas))+(2*Move_Down[1]+2))
            
            if down_two >= 239:
                down_two = down_one
        
        if x == 0: 
            Value_Area[canvas.index(max(canvas))] = [POC, canvas.index(max(canvas))]
            Value_Area_Volume += max(canvas)

        if up_one <= 0 or up_two <= 0:
            Move_Down = True, Move_Down[1]+1
            Value_Area[down_one] = [round((highest - (pricestep*(down_one))),2), canvas[down_one]]
            Value_Area[down_two] = [round((highest - (pricestep*(down_two))),2), canvas[down_two]]
            Value_Area_Volume += canvas[down_one] + canvas[down_two]
            continue

        elif down_one >= len(canvas) or down_two >= len(canvas):
            Move_Up = True, Move_Up[1]+1
            Value_Area[up_one] = [round((highest - (pricestep*(up_one))),2), canvas[up_one]]
            Value_Area[up_two] = [round((highest - (pricestep*(up_two))),2), canvas[up_two]]
            Value_Area_Volume += canvas[up_one] + canvas[up_two]
            continue
        
        if (canvas[up_one] + canvas[up_two]) > (canvas[down_one] + canvas[down_two]):
            Move_Up = True, Move_Up[1]+1
            Value_Area[up_one] = [round((highest - (pricestep*(up_one))),2), canvas[up_one]]
            Value_Area[up_two] = [round((highest - (pricestep*(up_two))),2), canvas[up_two]]
            Value_Area_Volume += canvas[up_one] + canvas[up_two]
        
        else:
            Move_Down = True, Move_Down[1]+1
            Value_Area[down_one] = [round((highest - (pricestep*(down_one))),2), canvas[down_one]]
            Value_Area[down_two] = [round((highest - (pricestep*(down_two))),2), canvas[down_two]]
            Value_Area_Volume += canvas[down_one] + canvas[down_two]

    VAH = round(max(Value_Area)[0], 1)
    VAL = round([x for x in Value_Area if x != [0, 0]][-1][0], 1)

    HIGH_BUCKET = "HIGH", sum([row[1] for row in Value_Area if VAH >= row[0] >= round(VAH - ((VAH - VAL)/3),2)]), VAH, round(VAH - ((VAH - VAL)/3),2)
    MID_BUCKET = "MID", sum([row[1] for row in Value_Area if round(VAH - ((VAH - VAL)/3),2) >= row[0] >= round(VAL + ((VAH - VAL)/3),2)]), round(VAH - ((VAH - VAL)/3),2) , round(VAL + ((VAH - VAL)/3),2)
    LOW_BUCKET = "LOW", sum([row[1] for row in Value_Area if round(VAL + ((VAH - VAL)/3),2) >= row[0] >= VAL]), round(VAL + ((VAH - VAL)/3),2) , VAL

    return round(POC, 1), VAH, VAL, list(max(HIGH_BUCKET, MID_BUCKET, LOW_BUCKET, key=lambda x:x[0]))
