
frappe.pages['assessment-dashboard'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Assessment Dashboard',
        single_column: true
    });

    // Fetch data
    frappe.call({
        method: 'numerouno.numerouno.page.assessment_dashboard.dashboard.get_assessments',
        callback: function(r) {
            if (r.message && r.message.length) {
                const table_html = `
                    <table class="table table-bordered">
                        <thead>
                            <tr>
                                <th>Assessment</th>
                                <th>Score</th>
                                <th>Total</th>
                                <th>Student</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${r.message.map(row => `
                                <tr>
                                    <td>${row.assessment_title}</td>
                                    <td>${row.score}</td>
                                    <td>${row.total}</td>
                                    <td>${row.student || '-'}</td>
                                    <td><a class="btn btn-primary btn-sm" href="/api/method/numerouno.api.download_certificate?name=${row.name}" target="_blank">Download PDF</a></td>
                                </tr>`).join('')}
                        </tbody>
                    </table>`;
                $(wrapper).find('.layout-main-section').html(table_html);
            } else {
                $(wrapper).find('.layout-main-section').html('<p>No assessment results available.</p>');
            }
        }
    });
};