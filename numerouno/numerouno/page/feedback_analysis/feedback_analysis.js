frappe.pages['feedback-analysis'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Feedback Analysis Dashboard',
		single_column: true
	});

	// Add CSS for better styling
	page.add_inner_button('Refresh Analysis', function() {
		load_feedback_analysis();
	}, 'btn-primary');

	// Create main container
	var main_container = $('<div class="feedback-analysis-container"></div>');
	page.main.append(main_container);

	// Create filters section
	var filters_section = $(`
		<div class="filters-section" style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
			<h4>📊 Analysis Filters</h4>
			<div class="row">
				<div class="col-md-3">
					<label>From Date:</label>
					<input type="date" class="form-control" id="from_date">
				</div>
				<div class="col-md-3">
					<label>To Date:</label>
					<input type="date" class="form-control" id="to_date">
				</div>
				<div class="col-md-3">
					<label>Student Group:</label>
					<select class="form-control" id="student_group">
						<option value="">All Groups</option>
					</select>
				</div>
				<div class="col-md-3">
					<label>&nbsp;</label><br>
					<button class="btn btn-primary btn-sm" onclick="load_feedback_analysis()">
						🔍 Analyze Feedback
					</button>
				</div>
			</div>
		</div>
	`);
	main_container.append(filters_section);

	// Create summary cards section
	var summary_section = $(`
		<div class="summary-section" style="margin-bottom: 20px;">
			<div class="row" id="summary_cards">
				<!-- Summary cards will be loaded here -->
			</div>
		</div>
	`);
	main_container.append(summary_section);

	// Create detailed analysis section
	var analysis_section = $(`
		<div class="analysis-section">
			<div class="row">
				<div class="col-md-8">
					<div class="card">
						<div class="card-header">
							<h5>🤖 AI-Powered Feedback Analysis</h5>
						</div>
						<div class="card-body" id="ai_analysis_content">
							<div class="text-center">
								<i class="fa fa-spinner fa-spin fa-2x"></i>
								<p>Loading AI analysis...</p>
							</div>
						</div>
					</div>
				</div>
				<div class="col-md-4">
					<div class="card">
						<div class="card-header">
							<h5>📈 Quick Stats</h5>
						</div>
						<div class="card-body" id="quick_stats">
							<!-- Quick stats will be loaded here -->
						</div>
					</div>
				</div>
			</div>
		</div>
	`);
	main_container.append(analysis_section);

	// Create feedback details section
	var details_section = $(`
		<div class="details-section" style="margin-top: 20px;">
			<div class="card">
				<div class="card-header">
					<h5>📝 Feedback Details</h5>
				</div>
				<div class="card-body">
					<div id="feedback_details">
						<!-- Feedback details will be loaded here -->
					</div>
				</div>
			</div>
		</div>
	`);
	main_container.append(details_section);

	// Load student groups
	load_student_groups();

	// Load initial analysis
	load_feedback_analysis();

	// Make function globally available
	window.load_feedback_analysis = load_feedback_analysis;

	function load_student_groups() {
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'Student Group',
				fields: ['name'],
				limit: 100
			},
			callback: function(r) {
				if (r.message) {
					var select = $('#student_group');
					r.message.forEach(function(group) {
						select.append(`<option value="${group.name}">${group.name}</option>`);
					});
				}
			}
		});
	}

	function load_feedback_analysis() {
		// Show loading state
		$('#ai_analysis_content').html(`
			<div class="text-center">
				<i class="fa fa-spinner fa-spin fa-2x"></i>
				<p>Analyzing feedback with AI...</p>
			</div>
		`);

		// Get filter values
		var filters = {
			from_date: $('#from_date').val(),
			to_date: $('#to_date').val(),
			student_group: $('#student_group').val()
		};

		// Use a simpler approach - get raw data and analyze locally
		get_feedback_data_and_analyze(filters);
	}

	function get_feedback_data_and_analyze(filters) {
		// Get detailed feedback data using server-side method
		frappe.call({
			method: 'numerouno.numerouno.page.feedback_analysis.feedback_analysis.get_feedback_data',
			args: {
				filters: filters
			},
			callback: function(r) {
				if (r.message) {
					// Process the data locally
					process_feedback_data(r.message, filters);
				} else {
					show_error("No data found or permission denied");
				}
			},
			error: function(err) {
				show_error("Error loading data: " + err.message);
			}
		});
	}

	function process_feedback_data(raw_data, filters) {
		// Group by feedback type
		var feedback_types = {};
		
		raw_data.forEach(function(row) {
			var feedback_type = row.course_feedback_type || 'Unknown';
			if (!feedback_types[feedback_type]) {
				feedback_types[feedback_type] = [];
			}
			feedback_types[feedback_type].push({
				feedback: row.feedback || '',
				posting_date: row.posting_date,
				student: row.student,
				student_group: row.student_group
			});
		});

		// Analyze each feedback type
		var analyzed_data = [];
		var total_feedback = 0;
		var total_negative = 0;

		Object.keys(feedback_types).forEach(function(feedback_type) {
			var entries = feedback_types[feedback_type];
			var negative_count = 0;
			var sentiment_scores = [];

			entries.forEach(function(entry) {
				var sentiment = analyze_sentiment(entry.feedback);
				sentiment_scores.push(sentiment);
				if (sentiment < -0.3) {
					negative_count++;
				}
			});

			var negative_percentage = (negative_count / entries.length) * 100;
			var avg_sentiment = sentiment_scores.reduce((a, b) => a + b, 0) / sentiment_scores.length;
			
			total_feedback += entries.length;
			total_negative += negative_count;

			// Get feedback texts for AI analysis
			var feedback_texts = entries.map(function(entry) {
				return entry.feedback || '';
			});

			analyzed_data.push({
				course_feedback_type: feedback_type,
				total_feedback: entries.length,
				negative_count: negative_count,
				negative_percentage: negative_percentage,
				avg_sentiment: avg_sentiment,
				priority_level: determine_priority_level(negative_percentage, avg_sentiment, entries.length),
				feedback_texts: feedback_texts, // Store for AI analysis
				key_issues: extract_key_issues(entries, negative_count),
				action_required: determine_action_required(negative_percentage, avg_sentiment)
			});
		});

		// Sort by priority
		analyzed_data.sort(function(a, b) {
			var priority_order = {"High": 1, "Medium": 2, "Low": 3};
			return priority_order[a.priority_level] - priority_order[b.priority_level];
		});

		// Update UI with initial data
		update_summary_cards(analyzed_data, total_feedback, total_negative);
		update_quick_stats(analyzed_data);
		update_feedback_details(analyzed_data);

		// Get AI analysis for each feedback type
		get_ai_analysis_for_all_types(analyzed_data);
	}

	function get_ai_analysis_for_all_types(analyzed_data) {
		// Show loading state for AI analysis
		$('#ai_analysis_content').html(`
			<div class="text-center">
				<i class="fa fa-spinner fa-spin fa-2x"></i>
				<p>Getting AI-powered analysis from Gemini...</p>
			</div>
		`);

		var promises = [];
		
		analyzed_data.forEach(function(data) {
			var promise = new Promise(function(resolve) {
				frappe.call({
					method: 'numerouno.numerouno.page.feedback_analysis.feedback_analysis.get_ai_analysis',
					args: {
						feedback_type: data.course_feedback_type,
						feedback_texts: data.feedback_texts,
						negative_percentage: data.negative_percentage
					},
					callback: function(r) {
						if (r.message) {
							data.ai_analysis = r.message;
						} else {
							data.ai_analysis = generate_ai_analysis(data.course_feedback_type, data.feedback_texts.map(function(text, index) {
								return { feedback: text };
							}), data.negative_percentage);
						}
						resolve();
					},
					error: function(err) {
						data.ai_analysis = generate_ai_analysis(data.course_feedback_type, data.feedback_texts.map(function(text, index) {
							return { feedback: text };
						}), data.negative_percentage);
						resolve();
					}
				});
			});
			promises.push(promise);
		});

		// Wait for all AI analysis to complete
		Promise.all(promises).then(function() {
			update_ai_analysis(analyzed_data);
		});
	}

	function analyze_sentiment(feedback) {
		if (!feedback) return 0;
		
		var feedback_lower = feedback.toLowerCase();
		var score = 0;
		var word_count = 0;
		
		// Negative phrases (higher weight)
		var negative_phrases = [
			'not good', 'not great', 'not excellent', 'not helpful', 'not useful',
			'bad attitude', 'poor attitude', 'terrible attitude',
			'take too much time', 'takes too long', 'very slow', 'too slow',
			'not satisfied', 'not happy', 'not pleased', 'disappointed',
			'not working', 'does not work', 'not functioning',
			'not professional', 'unprofessional', 'rude', 'impolite'
		];
		
		// Negative words (medium weight)
		var negative_words = [
			'bad', 'poor', 'terrible', 'awful', 'hate', 'difficult', 'confusing', 
			'boring', 'useless', 'problem', 'issue', 'complaint', 'disappointed', 
			'frustrated', 'annoying', 'slow', 'late', 'wrong', 'incorrect',
			'expensive', 'costly', 'waste', 'wasted', 'failed', 'failure',
			'broken', 'damaged', 'error', 'mistake', 'wrong', 'incorrect'
		];
		
		// Positive phrases (higher weight)
		var positive_phrases = [
			'very good', 'very great', 'very excellent', 'very helpful', 'very useful',
			'good attitude', 'great attitude', 'excellent attitude',
			'fast service', 'quick service', 'efficient', 'professional',
			'very satisfied', 'very happy', 'very pleased', 'excellent service',
			'working well', 'functions well', 'smooth process'
		];
		
		// Positive words (medium weight)
		var positive_words = [
			'good', 'great', 'excellent', 'amazing', 'helpful', 'useful', 'love', 
			'enjoy', 'like', 'perfect', 'outstanding', 'wonderful', 'fantastic',
			'fast', 'quick', 'efficient', 'smooth', 'easy', 'simple', 'clear',
			'professional', 'friendly', 'polite', 'courteous', 'satisfied', 'happy'
		];
		
		// Check for negative phrases first (higher weight)
		negative_phrases.forEach(function(phrase) {
			if (feedback_lower.includes(phrase)) {
				score -= 1.0; // Higher weight for phrases
				word_count++;
			}
		});
		
		// Check for positive phrases
		positive_phrases.forEach(function(phrase) {
			if (feedback_lower.includes(phrase)) {
				score += 1.0; // Higher weight for phrases
				word_count++;
			}
		});
		
		// Check for negative words
		negative_words.forEach(function(word) {
			if (feedback_lower.includes(word)) {
				score -= 0.6;
				word_count++;
			}
		});
		
		// Check for positive words
		positive_words.forEach(function(word) {
			if (feedback_lower.includes(word)) {
				score += 0.6;
				word_count++;
			}
		});
		
		// Special case: "not" followed by positive words
		var not_positive_pattern = /\bnot\s+(good|great|excellent|helpful|useful|satisfied|happy|pleased|working|professional)\b/gi;
		var not_matches = feedback_lower.match(not_positive_pattern);
		if (not_matches) {
			score -= 0.8 * not_matches.length;
			word_count += not_matches.length;
		}
		
		// Special case: "too" followed by negative words
		var too_negative_pattern = /\btoo\s+(slow|long|expensive|difficult|confusing|complicated)\b/gi;
		var too_matches = feedback_lower.match(too_negative_pattern);
		if (too_matches) {
			score -= 0.8 * too_matches.length;
			word_count += too_matches.length;
		}
		
		return word_count > 0 ? score / word_count : 0;
	}

	function determine_priority_level(negative_percentage, avg_sentiment, total_feedback) {
		if (negative_percentage >= 50 || avg_sentiment <= -0.5) {
			return "High";
		} else if (negative_percentage >= 25 || avg_sentiment <= -0.2) {
			return "Medium";
		} else {
			return "Low";
		}
	}

	function generate_ai_analysis(feedback_type, entries, negative_percentage) {
		var analysis = `📊 **${feedback_type} Feedback Analysis**\n\n`;
		
		if (negative_percentage > 50) {
			analysis += "🔴 **CRITICAL PRIORITY**\n";
			analysis += "• High negative feedback detected\n";
			analysis += "• Immediate attention required\n";
			analysis += "• Root cause analysis needed\n\n";
		} else if (negative_percentage > 25) {
			analysis += "🟡 **MODERATE PRIORITY**\n";
			analysis += "• Moderate negative feedback\n";
			analysis += "• Review and improvement needed\n";
			analysis += "• Monitor trends closely\n\n";
		} else {
			analysis += "🟢 **LOW PRIORITY**\n";
			analysis += "• Low negative feedback\n";
			analysis += "• Continue current practices\n";
			analysis += "• Minor optimizations only\n\n";
		}
		
		analysis += "🎯 **Key Themes Identified:**\n";
		var all_feedback = entries.map(e => e.feedback).join(' ').toLowerCase();
		
		var negative_words = ['bad', 'poor', 'terrible', 'awful', 'hate', 'difficult', 'confusing', 'boring', 'useless', 'problem', 'issue', 'complaint', 'disappointed', 'frustrated'];
		var positive_words = ['good', 'great', 'excellent', 'amazing', 'helpful', 'useful', 'love', 'enjoy', 'like', 'perfect', 'outstanding'];
		
		var found_negative = negative_words.filter(word => all_feedback.includes(word));
		var found_positive = positive_words.filter(word => all_feedback.includes(word));
		
		if (found_negative.length > 0) {
			analysis += `• Negative themes: ${found_negative.slice(0, 5).join(', ')}\n`;
		}
		if (found_positive.length > 0) {
			analysis += `• Positive themes: ${found_positive.slice(0, 5).join(', ')}\n`;
		}
		
		analysis += `\n⚠️ **Specific Issues:**\n`;
		analysis += `• ${negative_percentage.toFixed(1)}% of feedback is negative\n`;
		analysis += `• ${entries.length} total feedback entries\n`;
		analysis += `• ${Math.round(negative_percentage * entries.length / 100)} negative responses\n`;
		
		analysis += `\n💡 **Recommendations:**\n`;
		if (negative_percentage > 50) {
			analysis += "• Conduct immediate user interviews\n";
			analysis += "• Review and redesign the process\n";
			analysis += "• Implement quick fixes for urgent issues\n";
			analysis += "• Set up monitoring for improvements\n";
		} else if (negative_percentage > 25) {
			analysis += "• Gather more detailed feedback\n";
			analysis += "• Identify specific pain points\n";
			analysis += "• Implement targeted improvements\n";
			analysis += "• Follow up with affected users\n";
		} else {
			analysis += "• Continue current practices\n";
			analysis += "• Monitor for any changes\n";
			analysis += "• Consider minor optimizations\n";
		}
		
		return analysis;
	}

	function extract_key_issues(entries, negative_count) {
		if (negative_count === 0) return "No major issues identified";
		
		var negative_entries = entries.filter(entry => analyze_sentiment(entry.feedback) < -0.3);
		var issues = negative_entries.slice(0, 3).map(entry => {
			var feedback_text = entry.feedback.length > 100 ? entry.feedback.substring(0, 100) + '...' : entry.feedback;
			return `'${feedback_text}' (Student: ${entry.student})`;
		});
		
		return issues.join(' | ');
	}

	function determine_action_required(negative_percentage, avg_sentiment) {
		if (negative_percentage >= 70) {
			return "URGENT: Complete process review and immediate fixes required";
		} else if (negative_percentage >= 50) {
			return "CRITICAL: Major improvements needed - allocate resources";
		} else if (negative_percentage >= 30) {
			return "MODERATE: Review and implement targeted improvements";
		} else {
			return "LOW PRIORITY: Continue monitoring, minor optimizations";
		}
	}

	function update_summary_cards(data, total_feedback, total_negative) {
		var summary_html = '';
		
		// Total feedback types
		summary_html += `
			<div class="col-md-3">
				<div class="card text-center">
					<div class="card-body">
						<h3 class="text-info">${data.length}</h3>
						<p class="text-muted">Feedback Types</p>
					</div>
				</div>
			</div>
		`;
		
		// High priority types
		var high_priority = data.filter(d => d.priority_level === 'High').length;
		summary_html += `
			<div class="col-md-3">
				<div class="card text-center">
					<div class="card-body">
						<h3 class="text-danger">${high_priority}</h3>
						<p class="text-muted">High Priority Types</p>
					</div>
				</div>
			</div>
		`;
		
		// Total negative issues
		summary_html += `
			<div class="col-md-3">
				<div class="card text-center">
					<div class="card-body">
						<h3 class="text-danger">${total_negative}</h3>
						<p class="text-muted">Total Negative Issues</p>
					</div>
				</div>
			</div>
		`;
		
		// Most problematic type
		var most_problematic = data.length > 0 ? data[0] : null;
		if (most_problematic) {
			summary_html += `
				<div class="col-md-3">
					<div class="card text-center">
						<div class="card-body">
							<h3 class="text-warning">${most_problematic.course_feedback_type}</h3>
							<p class="text-muted">Most Problematic (${most_problematic.negative_percentage.toFixed(1)}% negative)</p>
						</div>
					</div>
				</div>
			`;
		}
		
		$('#summary_cards').html(summary_html);
	}

	function update_ai_analysis(data) {
		if (data && data.length > 0) {
			var analysis_html = '';
			data.forEach(function(row) {
				var priority_color = '';
				switch(row.priority_level) {
					case 'High': priority_color = 'text-danger'; break;
					case 'Medium': priority_color = 'text-warning'; break;
					case 'Low': priority_color = 'text-success'; break;
				}

				analysis_html += `
					<div class="feedback-type-analysis" style="margin-bottom: 30px; padding: 20px; border: 1px solid #e9ecef; border-radius: 8px;">
						<div class="d-flex justify-content-between align-items-center mb-3">
							<h4>${row.course_feedback_type}</h4>
							<span class="badge ${priority_color}">${row.priority_level} Priority</span>
						</div>
						
						<div class="row mb-3">
							<div class="col-md-3">
								<strong>Total Feedback:</strong> ${row.total_feedback}
							</div>
							<div class="col-md-3">
								<strong>Negative:</strong> ${row.negative_count} (${row.negative_percentage.toFixed(1)}%)
							</div>
							<div class="col-md-3">
								<strong>Avg Sentiment:</strong> ${row.avg_sentiment.toFixed(2)}
							</div>
							<div class="col-md-3">
								<strong>Action:</strong> ${row.action_required}
							</div>
						</div>

						<div class="ai-analysis-content" style="background: #f8f9fa; padding: 15px; border-radius: 5px; white-space: pre-line;">
							${row.ai_analysis || 'No AI analysis available'}
						</div>

						<div class="key-issues mt-3">
							<strong>Key Issues:</strong>
							<p>${row.key_issues || 'No specific issues identified'}</p>
						</div>
					</div>
				`;
			});
			$('#ai_analysis_content').html(analysis_html);
		} else {
			$('#ai_analysis_content').html(`
				<div class="text-center text-muted">
					<i class="fa fa-info-circle fa-2x"></i>
					<p>No feedback data found for the selected filters.</p>
				</div>
			`);
		}
	}

	function update_quick_stats(data) {
		if (data && data.length > 0) {
			var total_feedback = data.reduce((sum, row) => sum + row.total_feedback, 0);
			var total_negative = data.reduce((sum, row) => sum + row.negative_count, 0);
			var avg_negative_percentage = data.reduce((sum, row) => sum + row.negative_percentage, 0) / data.length;
			var high_priority_count = data.filter(row => row.priority_level === 'High').length;

			var stats_html = `
				<div class="quick-stat">
					<h4 class="text-primary">${total_feedback}</h4>
					<p>Total Feedback</p>
				</div>
				<hr>
				<div class="quick-stat">
					<h4 class="text-danger">${total_negative}</h4>
					<p>Negative Issues</p>
				</div>
				<hr>
				<div class="quick-stat">
					<h4 class="text-warning">${avg_negative_percentage.toFixed(1)}%</h4>
					<p>Avg Negative Rate</p>
				</div>
				<hr>
				<div class="quick-stat">
					<h4 class="text-danger">${high_priority_count}</h4>
					<p>High Priority Types</p>
				</div>
			`;
			$('#quick_stats').html(stats_html);
		}
	}

	function update_feedback_details(data) {
		if (data && data.length > 0) {
			var details_html = `
				<div class="table-responsive">
					<table class="table table-striped">
						<thead>
							<tr>
								<th>Feedback Type</th>
								<th>Total</th>
								<th>Negative</th>
								<th>Negative %</th>
								<th>Sentiment</th>
								<th>Priority</th>
								<th>Action Required</th>
							</tr>
						</thead>
						<tbody>
			`;

			data.forEach(function(row) {
				var priority_class = '';
				switch(row.priority_level) {
					case 'High': priority_class = 'text-danger'; break;
					case 'Medium': priority_class = 'text-warning'; break;
					case 'Low': priority_class = 'text-success'; break;
				}

				details_html += `
					<tr>
						<td><strong>${row.course_feedback_type}</strong></td>
						<td>${row.total_feedback}</td>
						<td>${row.negative_count}</td>
						<td>${row.negative_percentage.toFixed(1)}%</td>
						<td>${row.avg_sentiment.toFixed(2)}</td>
						<td><span class="${priority_class}">${row.priority_level}</span></td>
						<td>${row.action_required}</td>
					</tr>
				`;
			});

			details_html += `
						</tbody>
					</table>
				</div>
			`;
			$('#feedback_details').html(details_html);
		} else {
			$('#feedback_details').html(`
				<div class="text-center text-muted">
					<p>No feedback data available.</p>
				</div>
			`);
		}
	}

	function show_error(message) {
		$('#ai_analysis_content').html(`
			<div class="text-center text-danger">
				<i class="fa fa-exclamation-triangle fa-2x"></i>
				<p>${message}</p>
			</div>
		`);
	}
};