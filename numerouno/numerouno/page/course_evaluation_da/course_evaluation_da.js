frappe.pages['course-evaluation-da'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Course Evaluation Dashboard',
		single_column: true
	});

	// Add custom CSS
	add_custom_css();

	// Create dashboard container with proper structure
	let dashboard_container = $(`<div class="course-evaluation-dashboard">
		<div class="dashboard-filters"></div>
		<div class="dashboard-summary"></div>
		<div class="dashboard-charts"></div>
		<div class="dashboard-breakdown"></div>
		<div class="dashboard-detailed-analysis"></div>
	</div>`).appendTo(page.main);

	// Initialize dashboard
	init_dashboard(dashboard_container);
}

function add_custom_css() {
	let css = `
		<style>
			.course-evaluation-dashboard {
				padding: 15px;
			}
			
			.dashboard-filters .card {
				box-shadow: 0 2px 4px rgba(0,0,0,0.1);
				border: none;
				margin-bottom: 20px;
			}
			
			.dashboard-filters .card-header {
				background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
				color: white;
				border: none;
			}
			
			.summary-card {
				box-shadow: 0 2px 8px rgba(0,0,0,0.1);
				border: none;
				transition: transform 0.2s, box-shadow 0.2s;
				margin-bottom: 15px;
			}
			
			.summary-card:hover {
				transform: translateY(-5px);
				box-shadow: 0 4px 12px rgba(0,0,0,0.15);
			}
			
			.summary-card .card-body {
				padding: 20px;
			}
			
			.summary-card h3, .summary-card h4 {
				font-weight: 600;
				color: #2d3748;
			}
			
			.summary-card .text-muted {
				font-size: 0.85rem;
				color: #718096;
			}
			
			.dashboard-charts .card {
				box-shadow: 0 2px 4px rgba(0,0,0,0.1);
				border: none;
				margin-bottom: 20px;
			}
			
			.dashboard-charts .card-header {
				background: #f7fafc;
				border-bottom: 2px solid #e2e8f0;
				padding: 15px 20px;
			}
			
			.dashboard-charts .card-header h5 {
				margin: 0;
				font-weight: 600;
				color: #2d3748;
			}
			
			.dashboard-charts .card-body {
				padding: 20px;
			}
			
			.chart-container {
				min-height: 300px;
			}
			
			.dashboard-breakdown .card,
			.dashboard-detailed-analysis .card {
				box-shadow: 0 2px 4px rgba(0,0,0,0.1);
				border: none;
				margin-bottom: 20px;
			}
			
			.dashboard-breakdown .card-header,
			.dashboard-detailed-analysis .card-header {
				background: #f7fafc;
				border-bottom: 2px solid #e2e8f0;
				padding: 15px 20px;
			}
			
			.dashboard-breakdown .card-header h5,
			.dashboard-detailed-analysis .card-header h5 {
				margin: 0;
				font-weight: 600;
				color: #2d3748;
			}
			
			.dashboard-breakdown .card-body,
			.dashboard-detailed-analysis .card-body {
				padding: 20px;
			}
			
			.table-responsive {
				border-radius: 4px;
			}
			
			.table thead th {
				background-color: #2d3748;
				color: white;
				font-weight: 600;
				border: none;
				padding: 12px;
			}
			
			.table tbody tr {
				transition: background-color 0.2s;
			}
			
			.table tbody tr:hover {
				background-color: #f7fafc;
			}
			
			.badge {
				padding: 6px 12px;
				font-weight: 500;
			}
			
			.btn {
				border-radius: 4px;
				padding: 8px 16px;
				font-weight: 500;
			}
			
			.form-control {
				border-radius: 4px;
				border: 1px solid #cbd5e0;
			}
			
			.form-control:focus {
				border-color: #667eea;
				box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
			}
			
			.spinner-border-sm {
				width: 1.5rem;
				height: 1.5rem;
				border-width: 0.2em;
			}
		</style>
	`;
	
	$('head').append(css);
}

function init_dashboard(container) {
	// Create filters
	create_filters(container.find('.dashboard-filters'));
	
	// Create summary cards
	create_summary_cards(container.find('.dashboard-summary'));
	
	// Create charts
	create_charts(container.find('.dashboard-charts'));
	
	// Create breakdown section
	create_breakdown_section(container.find('.dashboard-breakdown'));
	
	// Create detailed analysis section
	create_detailed_analysis_section(container.find('.dashboard-detailed-analysis'));
	
	// Load initial data
	load_dashboard_data();
}

function create_filters(container) {
	let filters_html = `
		<div class="card mb-3">
			<div class="card-header">
				<h5 class="mb-0"><i class="fa fa-filter"></i> Filters</h5>
			</div>
			<div class="card-body">
				<div class="row">
					<div class="col-md-3">
						<div class="form-group">
							<label>From Date</label>
							<input type="date" class="form-control" id="from_date">
						</div>
					</div>
					<div class="col-md-3">
						<div class="form-group">
							<label>To Date</label>
							<input type="date" class="form-control" id="to_date">
						</div>
					</div>
					<div class="col-md-3">
						<div class="form-group">
							<label>Course</label>
							<input type="text" class="form-control" id="course" placeholder="Search Course...">
						</div>
					</div>
					<div class="col-md-3">
						<div class="form-group">
							<label>Instructor</label>
							<input type="text" class="form-control" id="instructor" placeholder="Search Instructor...">
						</div>
					</div>
				</div>
				<div class="row">
					<div class="col-md-3">
						<div class="form-group">
							<label>Company</label>
							<input type="text" class="form-control" id="company" placeholder="Search Company...">
						</div>
					</div>
					<div class="col-md-3">
						<div class="form-group">
							<label>Status</label>
							<select class="form-control" id="status">
								<option value="">All</option>
								<option value="1">Submitted</option>
								<option value="0">Draft</option>
							</select>
						</div>
					</div>
					<div class="col-md-6">
						<div class="form-group">
							<label>&nbsp;</label>
							<div>
								<button class="btn btn-primary" onclick="apply_filters()">
									<i class="fa fa-search"></i> Apply Filters
								</button>
								<button class="btn btn-secondary" onclick="clear_filters()">
									<i class="fa fa-times"></i> Clear
								</button>
								<button class="btn btn-info" onclick="refresh_data()">
									<i class="fa fa-refresh"></i> Refresh
								</button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	`;
	
	container.html(filters_html);
	
	// Don't set default dates - let user choose or show all data
}

function create_summary_cards(container) {
	let summary_html = `
		<div class="row">
			<div class="col-md-2">
				<div class="card summary-card">
					<div class="card-body">
						<div class="d-flex justify-content-between">
							<div>
								<h6 class="card-title text-muted">Total Evaluations</h6>
								<h3 class="mb-0" id="total_evaluations">0</h3>
								<small class="text-muted" id="total_trend">All time</small>
							</div>
							<div class="align-self-center">
								<i class="fa fa-clipboard-list fa-2x text-primary"></i>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-2">
				<div class="card summary-card">
					<div class="card-body">
						<div class="d-flex justify-content-between">
							<div>
								<h6 class="card-title text-muted">Submitted</h6>
								<h3 class="mb-0" id="submitted_evaluations">0</h3>
								<small class="text-muted" id="submitted_trend">Completed</small>
							</div>
							<div class="align-self-center">
								<i class="fa fa-check-circle fa-2x text-success"></i>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-2">
				<div class="card summary-card">
					<div class="card-body">
						<div class="d-flex justify-content-between">
							<div>
								<h6 class="card-title text-muted">Draft</h6>
								<h3 class="mb-0" id="draft_evaluations">0</h3>
								<small class="text-muted" id="draft_trend">In progress</small>
							</div>
							<div class="align-self-center">
								<i class="fa fa-edit fa-2x text-warning"></i>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-2">
				<div class="card summary-card">
					<div class="card-body">
						<div class="d-flex justify-content-between">
							<div>
								<h6 class="card-title text-muted">Average Rating</h6>
								<h3 class="mb-0" id="average_rating">0</h3>
								<small class="text-muted" id="rating_trend">Out of 4.0</small>
							</div>
							<div class="align-self-center">
								<i class="fa fa-star fa-2x text-info"></i>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-2">
				<div class="card summary-card">
					<div class="card-body">
						<div class="d-flex justify-content-between">
							<div>
								<h6 class="card-title text-muted">Excellent %</h6>
								<h3 class="mb-0" id="excellent_percentage">0%</h3>
								<small class="text-muted" id="excellent_trend">Percentage</small>
							</div>
							<div class="align-self-center">
								<i class="fa fa-trophy fa-2x text-success"></i>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-2">
				<div class="card summary-card">
					<div class="card-body">
						<div class="d-flex justify-content-between">
							<div>
								<h6 class="card-title text-muted">Courses</h6>
								<h3 class="mb-0" id="unique_courses">0</h3>
								<small class="text-muted" id="courses_trend">Unique courses</small>
							</div>
							<div class="align-self-center">
								<i class="fa fa-book fa-2x text-primary"></i>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="row mt-3">
			<div class="col-md-3">
				<div class="card summary-card">
					<div class="card-body">
						<div class="d-flex justify-content-between">
							<div>
								<h6 class="card-title text-muted">Instructors</h6>
								<h4 class="mb-0" id="unique_instructors">0</h4>
								<small class="text-muted">Unique instructors</small>
							</div>
							<div class="align-self-center">
								<i class="fa fa-user-tie fa-2x text-info"></i>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-3">
				<div class="card summary-card">
					<div class="card-body">
						<div class="d-flex justify-content-between">
							<div>
								<h6 class="card-title text-muted">Job Impact</h6>
								<h4 class="mb-0" id="improve_job_percentage">0%</h4>
								<small class="text-muted">Positive impact</small>
							</div>
							<div class="align-self-center">
								<i class="fa fa-briefcase fa-2x text-success"></i>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-3">
				<div class="card summary-card">
					<div class="card-body">
						<div class="d-flex justify-content-between">
							<div>
								<h6 class="card-title text-muted">Recommendation</h6>
								<h4 class="mb-0" id="recommend_percentage">0%</h4>
								<small class="text-muted">Would recommend</small>
							</div>
							<div class="align-self-center">
								<i class="fa fa-thumbs-up fa-2x text-primary"></i>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-3">
				<div class="card summary-card">
					<div class="card-body">
						<div class="d-flex justify-content-between">
							<div>
								<h6 class="card-title text-muted">Recent</h6>
								<h4 class="mb-0" id="recent_evaluations">0</h4>
								<small class="text-muted">Last 30 days</small>
							</div>
							<div class="align-self-center">
								<i class="fa fa-calendar-alt fa-2x text-info"></i>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	`;
	
	container.html(summary_html);
}

function create_charts(container) {
	let charts_html = `
		<div class="row">
			<div class="col-md-6">
				<div class="card">
					<div class="card-header">
						<h5>Rating Distribution</h5>
					</div>
					<div class="card-body">
						<div class="chart-container">
							<div id="rating-distribution-chart"></div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-6">
				<div class="card">
					<div class="card-header">
						<h5>Evaluations Over Time</h5>
					</div>
					<div class="card-body">
						<div class="chart-container">
							<div id="evaluations-over-time-chart"></div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="row mt-3">
			<div class="col-md-6">
				<div class="card">
					<div class="card-header">
						<h5>Top Performing Courses</h5>
					</div>
					<div class="card-body">
						<div class="chart-container">
							<div id="course-performance-chart"></div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-6">
				<div class="card">
					<div class="card-header">
						<h5>Instructor Performance</h5>
					</div>
					<div class="card-body">
						<div class="chart-container">
							<div id="instructor-performance-chart"></div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="row mt-3">
			<div class="col-md-4">
				<div class="card">
					<div class="card-header">
						<h5>Job Performance Impact</h5>
					</div>
					<div class="card-body">
						<div class="chart-container">
							<div id="job-impact-chart"></div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-4">
				<div class="card">
					<div class="card-header">
						<h5>Course Recommendations</h5>
					</div>
					<div class="card-body">
						<div class="chart-container">
							<div id="recommendations-chart"></div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-4">
				<div class="card">
					<div class="card-header">
						<h5>Course Duration Feedback</h5>
					</div>
					<div class="card-body">
						<div class="chart-container">
							<div id="duration-chart"></div>
						</div>
					</div>
				</div>
			</div>
		</div>
	`;
	
	container.html(charts_html);
}

function create_breakdown_section(container) {
	let breakdown_html = `
		<div class="row">
			<div class="col-md-6">
				<div class="card">
					<div class="card-header">
						<h5><i class="fa fa-trophy"></i> Top Performing Courses</h5>
					</div>
					<div class="card-body">
						<div id="top_courses_table">
							<div class="text-center p-3">
								<div class="spinner-border spinner-border-sm" role="status"></div>
								<p class="mt-2">Loading course data...</p>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-6">
				<div class="card">
					<div class="card-header">
						<h5><i class="fa fa-user-tie"></i> Top Instructors</h5>
					</div>
					<div class="card-body">
						<div id="top_instructors_table">
							<div class="text-center p-3">
								<div class="spinner-border spinner-border-sm" role="status"></div>
								<p class="mt-2">Loading instructor data...</p>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="row mt-3">
			<div class="col-md-6">
				<div class="card">
					<div class="card-header">
						<h5><i class="fa fa-building"></i> Company-wise Evaluations</h5>
					</div>
					<div class="card-body">
						<div id="company_evaluations_table">
							<div class="text-center p-3">
								<div class="spinner-border spinner-border-sm" role="status"></div>
								<p class="mt-2">Loading company data...</p>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-6">
				<div class="card">
					<div class="card-header">
						<h5><i class="fa fa-star"></i> Category-wise Ratings</h5>
					</div>
					<div class="card-body">
						<div id="category_ratings_table">
							<div class="text-center p-3">
								<div class="spinner-border spinner-border-sm" role="status"></div>
								<p class="mt-2">Loading category data...</p>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	`;
	
	container.html(breakdown_html);
}

function create_detailed_analysis_section(container) {
	let analysis_html = `
		<div class="row">
			<div class="col-12">
				<h3 class="text-center mb-4"><i class="fa fa-chart-bar"></i> Detailed Analysis</h3>
			</div>
		</div>
		
		<div class="row">
			<div class="col-md-6">
				<div class="card">
					<div class="card-header">
						<h5><i class="fa fa-chart-pie"></i> Rating Breakdown</h5>
					</div>
					<div class="card-body">
						<div id="rating_breakdown_table">
							<div class="text-center p-3">
								<div class="spinner-border spinner-border-sm" role="status"></div>
								<p class="mt-2">Loading rating breakdown...</p>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-6">
				<div class="card">
					<div class="card-header">
						<h5><i class="fa fa-tasks"></i> Training Impact Analysis</h5>
					</div>
					<div class="card-body">
						<div id="training_impact_table">
							<div class="text-center p-3">
								<div class="spinner-border spinner-border-sm" role="status"></div>
								<p class="mt-2">Loading impact analysis...</p>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		
		<div class="row mt-3">
			<div class="col-md-6">
				<div class="card">
					<div class="card-header">
						<h5><i class="fa fa-clock"></i> Duration Feedback Analysis</h5>
					</div>
					<div class="card-body">
						<div id="duration_analysis_table">
							<div class="text-center p-3">
								<div class="spinner-border spinner-border-sm" role="status"></div>
								<p class="mt-2">Loading duration analysis...</p>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="col-md-6">
				<div class="card">
					<div class="card-header">
						<h5><i class="fa fa-chart-line"></i> Performance Trends</h5>
					</div>
					<div class="card-body">
						<div id="performance_trends_table">
							<div class="text-center p-3">
								<div class="spinner-border spinner-border-sm" role="status"></div>
								<p class="mt-2">Loading trends...</p>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	`;
	
	container.html(analysis_html);
}

function load_dashboard_data() {
	let filters = get_filters();
	
	frappe.call({
		method: 'numerouno.numerouno.page.course_evaluation_da.course_evaluation_da.get_dashboard_data',
		args: {
			filters: filters
		},
		callback: function(r) {
			if (r.message) {
				try {
					window.current_dashboard_data = r.message;
					update_summary_cards(r.message.summary || {});
					update_charts(r.message);
					update_breakdown_section(r.message);
					update_detailed_analysis_section(r.message);
				} catch (error) {
					console.error('Error updating dashboard:', error);
					frappe.show_alert({
						message: 'Error updating dashboard: ' + error.message,
						indicator: 'red'
					}, 5);
				}
			}
		},
		error: function(err) {
			console.error('API Error:', err);
			frappe.show_alert({
				message: 'Error loading dashboard data',
				indicator: 'red'
			}, 5);
		}
	});
}

function get_filters() {
	let filters = {};
	
	// Only include non-empty values
	if ($('#from_date').val()) {
		filters.from_date = $('#from_date').val();
	}
	if ($('#to_date').val()) {
		filters.to_date = $('#to_date').val();
	}
	if ($('#course').val()) {
		filters.course = $('#course').val();
	}
	if ($('#instructor').val()) {
		filters.instructor = $('#instructor').val();
	}
	if ($('#company').val()) {
		filters.company = $('#company').val();
	}
	if ($('#status').val()) {
		filters.status = $('#status').val();
	}
	
	return filters;
}

function update_summary_cards(summary) {
	$('#total_evaluations').text(summary.total_evaluations || 0);
	$('#submitted_evaluations').text(summary.submitted_evaluations || 0);
	$('#draft_evaluations').text(summary.draft_evaluations || 0);
	$('#average_rating').text(summary.average_rating || 0);
	$('#excellent_percentage').text((summary.excellent_percentage || 0) + '%');
	$('#unique_courses').text(summary.unique_courses || 0);
	$('#unique_instructors').text(summary.unique_instructors || 0);
	$('#improve_job_percentage').text((summary.improve_job_percentage || 0) + '%');
	$('#recommend_percentage').text((summary.recommend_percentage || 0) + '%');
	$('#recent_evaluations').text(summary.recent_evaluations || 0);
}

function update_charts(data) {
	// Rating Distribution Chart
	frappe.call({
		method: "numerouno.numerouno.page.course_evaluation_da.course_evaluation_da.get_rating_distribution",
		callback: function(r) {
			if (r.message && r.message.labels && r.message.labels.length > 0) {
				let chart = new frappe.Chart("#rating-distribution-chart", {
					data: r.message,
					type: 'pie',
					colors: ['#10b981', '#3b82f6', '#f59e0b', '#ef4444'],
					height: 300
				});
			}
		}
	});

	// Evaluations Over Time Chart
	frappe.call({
		method: "numerouno.numerouno.page.course_evaluation_da.course_evaluation_da.get_evaluations_over_time",
		callback: function(r) {
			if (r.message && r.message.labels && r.message.labels.length > 0) {
				let chart = new frappe.Chart("#evaluations-over-time-chart", {
					data: r.message,
					type: 'line',
					colors: ['#3b82f6'],
					height: 300
				});
			}
		}
	});

	// Course Performance Chart
	frappe.call({
		method: "numerouno.numerouno.page.course_evaluation_da.course_evaluation_da.get_course_performance",
		callback: function(r) {
			if (r.message && r.message.labels && r.message.labels.length > 0) {
				let chart = new frappe.Chart("#course-performance-chart", {
					data: r.message,
					type: 'bar',
					colors: ['#10b981'],
					height: 300
				});
			}
		}
	});

	// Instructor Performance Chart
	frappe.call({
		method: "numerouno.numerouno.page.course_evaluation_da.course_evaluation_da.get_instructor_performance",
		callback: function(r) {
			if (r.message && r.message.labels && r.message.labels.length > 0) {
				let chart = new frappe.Chart("#instructor-performance-chart", {
					data: r.message,
					type: 'bar',
					colors: ['#3b82f6', '#10b981'],
					height: 300
				});
			}
		}
	});

	// Training Impact Charts
	frappe.call({
		method: "numerouno.numerouno.page.course_evaluation_da.course_evaluation_da.get_training_impact_metrics",
		callback: function(r) {
			if (r.message) {
				if (r.message.improve_job && r.message.improve_job.labels && r.message.improve_job.labels.length > 0) {
					let job_data = {
						labels: r.message.improve_job.labels,
						datasets: [{
							name: "Job Performance Impact",
							values: r.message.improve_job.values
						}]
					};
					let job_chart = new frappe.Chart("#job-impact-chart", {
						data: job_data,
						type: 'pie',
						colors: ['#10b981', '#ef4444', '#f59e0b'],
						height: 250
					});
				}

				if (r.message.recommend && r.message.recommend.labels && r.message.recommend.labels.length > 0) {
					let rec_data = {
						labels: r.message.recommend.labels,
						datasets: [{
							name: "Recommendations",
							values: r.message.recommend.values
						}]
					};
					let rec_chart = new frappe.Chart("#recommendations-chart", {
						data: rec_data,
						type: 'pie',
						colors: ['#10b981', '#ef4444', '#f59e0b'],
						height: 250
					});
				}

				if (r.message.duration && r.message.duration.labels && r.message.duration.labels.length > 0) {
					let dur_data = {
						labels: r.message.duration.labels,
						datasets: [{
							name: "Course Duration",
							values: r.message.duration.values
						}]
					};
					let dur_chart = new frappe.Chart("#duration-chart", {
						data: dur_data,
						type: 'pie',
						colors: ['#f59e0b', '#10b981', '#3b82f6'],
						height: 250
					});
				}
			}
		}
	});
}

function update_breakdown_section(data) {
	// Top Courses
	frappe.call({
		method: "numerouno.numerouno.page.course_evaluation_da.course_evaluation_da.get_course_performance",
		callback: function(r) {
			if (r.message && r.message.labels && r.message.labels.length > 0) {
				let table_html = `
					<div class="table-responsive">
						<table class="table table-sm table-striped">
							<thead class="thead-dark">
								<tr>
									<th>Rank</th>
									<th>Course</th>
									<th>Avg Rating</th>
									<th>Performance</th>
								</tr>
							</thead>
							<tbody>
				`;
				
				r.message.labels.forEach((course, index) => {
					let rating = r.message.datasets[0].values[index] || 0;
					let performance = rating >= 3.5 ? 'Excellent' : rating >= 3.0 ? 'Good' : rating >= 2.5 ? 'Average' : 'Poor';
					let badge_class = rating >= 3.5 ? 'badge-success' : rating >= 3.0 ? 'badge-info' : rating >= 2.5 ? 'badge-warning' : 'badge-danger';
					
					table_html += `
						<tr>
							<td><strong>#${index + 1}</strong></td>
							<td>${course}</td>
							<td>${rating.toFixed(2)}</td>
							<td><span class="badge ${badge_class}">${performance}</span></td>
						</tr>
					`;
				});
				
				table_html += '</tbody></table></div>';
				$('#top_courses_table').html(table_html);
			}
		}
	});

	// Top Instructors
	frappe.call({
		method: "numerouno.numerouno.page.course_evaluation_da.course_evaluation_da.get_instructor_performance",
		callback: function(r) {
			if (r.message && r.message.labels && r.message.labels.length > 0) {
				let table_html = `
					<div class="table-responsive">
						<table class="table table-sm table-striped">
							<thead class="thead-dark">
								<tr>
									<th>Rank</th>
									<th>Instructor</th>
									<th>Presentation</th>
									<th>Teaching</th>
									<th>Avg Score</th>
								</tr>
							</thead>
							<tbody>
				`;
				
				r.message.labels.forEach((instructor, index) => {
					let presentation = r.message.datasets[0].values[index] || 0;
					let teaching = r.message.datasets[1].values[index] || 0;
					let avg = (presentation + teaching) / 2;
					let badge_class = avg >= 3.5 ? 'badge-success' : avg >= 3.0 ? 'badge-info' : avg >= 2.5 ? 'badge-warning' : 'badge-danger';
					
					table_html += `
						<tr>
							<td><strong>#${index + 1}</strong></td>
							<td>${instructor}</td>
							<td>${presentation.toFixed(2)}</td>
							<td>${teaching.toFixed(2)}</td>
							<td><span class="badge ${badge_class}">${avg.toFixed(2)}</span></td>
						</tr>
					`;
				});
				
				table_html += '</tbody></table></div>';
				$('#top_instructors_table').html(table_html);
			}
		}
	});

	// Company Evaluations
	frappe.call({
		method: "numerouno.numerouno.page.course_evaluation_da.course_evaluation_da.get_company_evaluations",
		callback: function(r) {
			if (r.message && r.message.labels && r.message.labels.length > 0) {
				let table_html = `
					<div class="table-responsive">
						<table class="table table-sm table-striped">
							<thead class="thead-dark">
								<tr>
									<th>Company</th>
									<th>Evaluations</th>
									<th>Percentage</th>
								</tr>
							</thead>
							<tbody>
				`;
				
				let total = r.message.datasets[0].values.reduce((a, b) => a + b, 0);
				r.message.labels.forEach((company, index) => {
					let count = r.message.datasets[0].values[index] || 0;
					let percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
					
					table_html += `
						<tr>
							<td>${company}</td>
							<td>${count}</td>
							<td>${percentage}%</td>
						</tr>
					`;
				});
				
				table_html += '</tbody></table></div>';
				$('#company_evaluations_table').html(table_html);
			}
		}
	});

	// Category Ratings
	frappe.call({
		method: "numerouno.numerouno.page.course_evaluation_da.course_evaluation_da.get_category_ratings",
		callback: function(r) {
			if (r.message && r.message.labels && r.message.labels.length > 0) {
				let table_html = `
					<div class="table-responsive">
						<table class="table table-sm table-striped">
							<thead class="thead-dark">
								<tr>
									<th>Category</th>
									<th>Avg Rating</th>
									<th>Performance</th>
								</tr>
							</thead>
							<tbody>
				`;
				
				r.message.labels.forEach((category, index) => {
					let rating = r.message.datasets[0].values[index] || 0;
					let performance = rating >= 3.5 ? 'Excellent' : rating >= 3.0 ? 'Good' : rating >= 2.5 ? 'Average' : 'Poor';
					let badge_class = rating >= 3.5 ? 'badge-success' : rating >= 3.0 ? 'badge-info' : rating >= 2.5 ? 'badge-warning' : 'badge-danger';
					
					table_html += `
						<tr>
							<td>${category}</td>
							<td>${rating.toFixed(2)}</td>
							<td><span class="badge ${badge_class}">${performance}</span></td>
						</tr>
					`;
				});
				
				table_html += '</tbody></table></div>';
				$('#category_ratings_table').html(table_html);
			}
		}
	});
}

function update_detailed_analysis_section(data) {
	// Rating Breakdown
	frappe.call({
		method: "numerouno.numerouno.page.course_evaluation_da.course_evaluation_da.get_detailed_metrics",
		callback: function(r) {
			if (r.message) {
				let table_html = `
					<div class="table-responsive">
						<table class="table table-sm table-striped">
							<thead class="thead-dark">
								<tr>
									<th>Rating</th>
									<th>Count</th>
									<th>Percentage</th>
								</tr>
							</thead>
							<tbody>
								<tr>
									<td><strong>Excellent</strong></td>
									<td>${r.message.excellent_count || 0}</td>
									<td>${r.message.excellent_percentage || 0}%</td>
								</tr>
								<tr>
									<td><strong>Good</strong></td>
									<td>${r.message.good_count || 0}</td>
									<td>${r.message.good_percentage || 0}%</td>
								</tr>
								<tr>
									<td><strong>Average</strong></td>
									<td>${r.message.average_count || 0}</td>
									<td>${r.message.average_percentage || 0}%</td>
								</tr>
								<tr>
									<td><strong>Poor</strong></td>
									<td>${r.message.poor_count || 0}</td>
									<td>${r.message.poor_percentage || 0}%</td>
								</tr>
							</tbody>
						</table>
					</div>
				`;
				$('#rating_breakdown_table').html(table_html);
			}
		}
	});

	// Training Impact
	frappe.call({
		method: "numerouno.numerouno.page.course_evaluation_da.course_evaluation_da.get_detailed_metrics",
		callback: function(r) {
			if (r.message) {
				let table_html = `
					<div class="table-responsive">
						<table class="table table-sm table-striped">
							<thead class="thead-dark">
								<tr>
									<th>Metric</th>
									<th>Count</th>
									<th>Status</th>
								</tr>
							</thead>
							<tbody>
								<tr>
									<td><strong>Will Improve Job</strong></td>
									<td>${r.message.improve_job_yes || 0}</td>
									<td><span class="badge badge-success">Positive</span></td>
								</tr>
								<tr>
									<td><strong>Would Recommend</strong></td>
									<td>${r.message.recommend_yes || 0}</td>
									<td><span class="badge badge-success">Positive</span></td>
								</tr>
								<tr>
									<td><strong>Maybe Improve</strong></td>
									<td>${r.message.improve_job_maybe || 0}</td>
									<td><span class="badge badge-warning">Neutral</span></td>
								</tr>
								<tr>
									<td><strong>Won't Improve</strong></td>
									<td>${r.message.improve_job_no || 0}</td>
									<td><span class="badge badge-danger">Negative</span></td>
								</tr>
							</tbody>
						</table>
					</div>
				`;
				$('#training_impact_table').html(table_html);
			}
		}
	});

	// Duration Analysis
	frappe.call({
		method: "numerouno.numerouno.page.course_evaluation_da.course_evaluation_da.get_detailed_metrics",
		callback: function(r) {
			if (r.message) {
				let table_html = `
					<div class="table-responsive">
						<table class="table table-sm table-striped">
							<thead class="thead-dark">
								<tr>
									<th>Duration</th>
									<th>Count</th>
									<th>Feedback</th>
								</tr>
							</thead>
							<tbody>
								<tr>
									<td><strong>About Right</strong></td>
									<td>${r.message.duration_about_right || 0}</td>
									<td><span class="badge badge-success">Good</span></td>
								</tr>
								<tr>
									<td><strong>Too Long</strong></td>
									<td>${r.message.duration_too_long || 0}</td>
									<td><span class="badge badge-warning">Needs Review</span></td>
								</tr>
								<tr>
									<td><strong>Too Short</strong></td>
									<td>${r.message.duration_short || 0}</td>
									<td><span class="badge badge-info">Consider Extension</span></td>
								</tr>
							</tbody>
						</table>
					</div>
				`;
				$('#duration_analysis_table').html(table_html);
			}
		}
	});

	// Performance Trends
	frappe.call({
		method: "numerouno.numerouno.page.course_evaluation_da.course_evaluation_da.get_evaluations_over_time",
		callback: function(r) {
			if (r.message && r.message.labels && r.message.labels.length > 0) {
				let table_html = `
					<div class="table-responsive">
						<table class="table table-sm table-striped">
							<thead class="thead-dark">
								<tr>
									<th>Month</th>
									<th>Evaluations</th>
									<th>Trend</th>
								</tr>
							</thead>
							<tbody>
				`;
				
				r.message.labels.forEach((month, index) => {
					let count = r.message.datasets[0].values[index] || 0;
					let trend = index > 0 ? (count > r.message.datasets[0].values[index-1] ? '↗️' : count < r.message.datasets[0].values[index-1] ? '↘️' : '→') : '→';
					
					table_html += `
						<tr>
							<td>${month}</td>
							<td>${count}</td>
							<td>${trend}</td>
						</tr>
					`;
				});
				
				table_html += '</tbody></table></div>';
				$('#performance_trends_table').html(table_html);
			}
		}
	});
}

function apply_filters() {
	load_dashboard_data();
}

function clear_filters() {
	$('#from_date').val('');
	$('#to_date').val('');
	$('#course').val('');
	$('#instructor').val('');
	$('#company').val('');
	$('#status').val('');
	load_dashboard_data();
}

function refresh_data() {
	load_dashboard_data();
}

// Global functions
window.apply_filters = apply_filters;
window.clear_filters = clear_filters;
window.refresh_data = refresh_data;
