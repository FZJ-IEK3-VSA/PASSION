import matplotlib.colors
import numpy as np
import passion

def open_csv_results(results_path, filename):
    if (results_path / filename).is_file():
        # exists
        results = passion.util.io.load_csv(results_path, filename)
    else:
        # does not exist
        results = None
    
    return results

def rooftop_popup_html(table_dict, table_size=(200,60)):
    left_col_color = "#19a7bd"
    right_col_color = "#f2f0d3"

    name = table_dict.pop('name')
    
    html_rows = ""
    for key, value in table_dict.items():
        html_row = """
<tr>
<td style="background-color: """+ left_col_color +""";text-align: center"><span style="color: #ffffff;">{0}</span></td>
<td style="width: 150px;background-color: """.format(key)+ right_col_color +""";text-align: center">{0}</td>""".format(value) + """
</tr>
        """
        html_rows += html_row

    html = """<!DOCTYPE html>
<html>
<head>
<h4 style="margin-bottom:10"; width="200px">{}</h4>""".format(name) + """
</head>
    <table style="height: {0}px; width: {1}px;">
<tbody>
{2}
</tbody>
</table>
</html>
""".format(table_size[1], table_size[0], html_rows)
    return html

def create_gradient_from_column(outlines, column, min_color, max_color):
    min_value = 9999999999999999999999999999
    max_value = -999999999999999999999999999
    # get min and max values for column
    for section in outlines:
        if section[column] > max_value: max_value = section[column]
        if section[column] < min_value: min_value = section[column]
    # normalize value between 0 and 1
    for section in outlines:
        norm_value = (section[column] - min_value) / (max_value - min_value)
        #if (norm_value != 0): math.log(10*norm_value, 10)
        color = color_fader(min_color, max_color, norm_value)
        section['color'] = color
        
    return

# https://stackoverflow.com/a/50784012
def color_fader(c1,c2,mix=0): #fade (linear interpolate) from color c1 (at mix=0) to c2 (mix=1)
    c1=np.array(matplotlib.colors.to_rgb(c1))
    c2=np.array(matplotlib.colors.to_rgb(c2))
    return matplotlib.colors.to_hex((1-mix)*c1 + mix*c2)