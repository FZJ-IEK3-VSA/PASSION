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
<h4 style="margin-bottom:10"; width="200px">{}</h4>""".format('Rooftop') + """
</head>
    <table style="height: {0}px; width: {1}px;">
<tbody>
{2}
</tbody>
</table>
</html>
""".format(table_size[1], table_size[0], html_rows)
    return html