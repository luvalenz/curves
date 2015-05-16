createChart = function(id, data){
    nv.addGraph(function() {
    var chart = nv.models.scatterChart()
                .showDistX(true)
                .showDistY(true)
                .color(d3.scale.category10().range());

    chart.xAxis.tickFormat(d3.format('.02f'));
    chart.yAxis.tickFormat(d3.format('.02f'));

    d3.select('#chart'+ id + ' svg')
      .datum(data)
    .transition().duration(500)
      .call(chart);

    nv.utils.windowResize(chart.update);

    return chart;
});
};