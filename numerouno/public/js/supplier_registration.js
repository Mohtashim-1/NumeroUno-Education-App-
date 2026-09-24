(() => {
	const { createApp, ref, reactive, onMounted } = Vue;
	const API = "numerouno.numerouno.api.supplier_registration";

	function csrf() {
		return document.querySelector('meta[name="csrf-token"]')?.content || "";
	}

	async function call(method, args = {}) {
		const res = await fetch(`/api/method/${API}.${method}`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				Accept: "application/json",
				"X-Frappe-CSRF-Token": csrf(),
			},
			credentials: "same-origin",
			body: JSON.stringify(args),
		});
		const data = await res.json();
		if (!res.ok || data.exc) {
			let message = "Request failed";
			try {
				if (data._server_messages) {
					const msgs = JSON.parse(data._server_messages);
					message = JSON.parse(msgs[0]).message || message;
				}
			} catch (e) {
				message = data.message || message;
			}
			throw new Error(message);
		}
		return data.message;
	}

	const EMPTY = () => ({
		supplier_name: "",
		supplier_type: "Company",
		trade_license: "",
		tax_id: "",
		country: "United Arab Emirates",
		city: "",
		emirate: "Abu Dhabi",
		contact_person: "",
		email: "",
		mobile_no: "",
		phone: "",
		address_line1: "",
		address_line2: "",
		bank_name: "",
		iban: "",
		account_name: "",
		payment_terms: "Net 30",
		goods_services: "",
		remarks: "",
		trade_license_valid_until: "",
		icv_valid_until: "",
	});

	createApp({
		setup() {
			const brand = reactive({
				name: "NumeroUNO",
				company_name: "Numero Uno Training and Consulting LLC",
				tagline: "Supplier Registration",
				logo: "/assets/numerouno/images/numero-logo.png",
			});
			const f = reactive(EMPTY());
			const files = reactive({
				trade_license_attachment: null,
				tax_registration_certificate: null,
				icv_certificate: null,
				iban_letter: null,
				additional_documents: null,
			});
			const errors = reactive({});
			const submitting = ref(false);
			const done = ref(false);
			const refName = ref("");
			const emirates = ref([
				"Abu Dhabi",
				"Dubai",
				"Sharjah",
				"Ajman",
				"Umm Al Quwain",
				"Ras Al Khaimah",
				"Fujairah",
			]);
			const formError = ref("");

			const onFile = (key, e) => {
				files[key] = e.target.files?.[0] || null;
			};

			const validate = () => {
				Object.keys(errors).forEach((k) => delete errors[k]);
				formError.value = "";
				const req = [
					["supplier_name", "Company name is required"],
					["contact_person", "Contact person is required"],
					["email", "Email is required"],
					["mobile_no", "Mobile is required"],
					["address_line1", "Address is required"],
					["city", "City is required"],
				];
				req.forEach(([k, msg]) => {
					if (!(f[k] || "").trim()) errors[k] = msg;
				});
				if (f.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email.trim())) {
					errors.email = "Enter a valid email";
				}
				if (!files.trade_license_attachment) errors.trade_license_attachment = "Trade License is required";
				if (!f.trade_license_valid_until) errors.trade_license_valid_until = "Validity date is required";
				if (!files.tax_registration_certificate)
					errors.tax_registration_certificate = "Tax Registration Certificate is required";
				if (!files.icv_certificate) errors.icv_certificate = "ICV Certificate is required";
				if (!f.icv_valid_until) errors.icv_valid_until = "Validity date is required";
				if (!files.iban_letter) errors.iban_letter = "IBAN Letter is required";
				return Object.keys(errors).length === 0;
			};

			const submit = async () => {
				if (!validate()) return;
				submitting.value = true;
				formError.value = "";
				try {
					const fd = new FormData();
					Object.entries(f).forEach(([k, v]) => {
						if (v != null && v !== "") fd.append(k, v);
					});
					Object.entries(files).forEach(([k, file]) => {
						if (file) fd.append(k, file, file.name);
					});
					const res = await fetch(`/api/method/${API}.submit_supplier_registration`, {
						method: "POST",
						headers: {
							Accept: "application/json",
							"X-Frappe-CSRF-Token": csrf(),
						},
						credentials: "same-origin",
						body: fd,
					});
					const data = await res.json();
					if (!res.ok || data.exc) {
						let message = "Submission failed";
						try {
							if (data._server_messages) {
								const msgs = JSON.parse(data._server_messages);
								message = JSON.parse(msgs[0]).message || message;
							}
						} catch (e) {
							message = data.message || message;
						}
						throw new Error(message);
					}
					refName.value = data.message?.name || "";
					done.value = true;
				} catch (e) {
					formError.value = e.message || "Submission failed";
				} finally {
					submitting.value = false;
				}
			};

			const reset = () => {
				Object.assign(f, EMPTY());
				Object.keys(files).forEach((k) => (files[k] = null));
				done.value = false;
				refName.value = "";
				formError.value = "";
			};

			onMounted(async () => {
				try {
					const ctx = await call("get_registration_context");
					if (ctx?.emirates?.length) emirates.value = ctx.emirates;
					if (ctx?.portal_name) brand.name = ctx.portal_name;
					if (ctx?.company_name) brand.company_name = ctx.company_name;
					if (ctx?.tagline) brand.tagline = ctx.tagline;
					if (ctx?.logo) brand.logo = ctx.logo;
				} catch (e) {
					/* defaults ok */
				}
			});

			return { brand, f, files, errors, submitting, done, refName, emirates, formError, submit, reset, onFile };
		},
		template: `
<div class="sip-shell" style="min-height:100vh">
  <header class="sip-header">
    <div class="sip-brand">
      <img class="sip-brand-logo" :src="brand.logo" :alt="brand.company_name" />
      <div class="sip-brand-text">
        <strong>{{ brand.name }}</strong>
        <span class="sip-company">{{ brand.company_name }}</span>
        <span class="sip-tagline">{{ brand.tagline }}</span>
      </div>
    </div>
    <div class="sip-header-user">
      <a href="/supplier-invoice-portal" style="color:#fff;text-decoration:none;font-size:14px">Invoice Portal →</a>
    </div>
  </header>
  <div class="sr-wrap">
    <div class="sr-topbar">
      <div>
        <h1 class="sip-title" style="margin:0">Register as a Supplier</h1>
        <p class="sip-sub" style="margin:6px 0 0">Submit your company details to <strong>{{ brand.company_name }}</strong>. Our AP team will review and approve your account.</p>
      </div>
    </div>

    <section v-if="!done" class="sr-card">
      <div class="sr-grid">
        <div class="sr-section">Company</div>
        <div class="sr-field sr-full">
          <label>Supplier / Company Name <span class="req">*</span></label>
          <input v-model="f.supplier_name" placeholder="Legal company name" />
          <div v-if="errors.supplier_name" class="sr-err">{{ errors.supplier_name }}</div>
        </div>
        <div class="sr-field">
          <label>Supplier Type</label>
          <select v-model="f.supplier_type"><option>Company</option><option>Individual</option></select>
        </div>
        <div class="sr-field">
          <label>Trade License No.</label>
          <input v-model="f.trade_license" />
        </div>
        <div class="sr-field">
          <label>Tax / VAT Number</label>
          <input v-model="f.tax_id" />
        </div>
        <div class="sr-field">
          <label>Preferred Payment Terms</label>
          <select v-model="f.payment_terms"><option>Net 30</option><option>Net 45</option><option>Net 60</option><option>Immediate</option></select>
        </div>

        <div class="sr-section">Primary Contact</div>
        <div class="sr-field">
          <label>Contact Person <span class="req">*</span></label>
          <input v-model="f.contact_person" />
          <div v-if="errors.contact_person" class="sr-err">{{ errors.contact_person }}</div>
        </div>
        <div class="sr-field">
          <label>Email <span class="req">*</span></label>
          <input v-model="f.email" type="email" placeholder="ap@supplier.com" />
          <div v-if="errors.email" class="sr-err">{{ errors.email }}</div>
        </div>
        <div class="sr-field">
          <label>Mobile <span class="req">*</span></label>
          <input v-model="f.mobile_no" placeholder="+971 …" />
          <div v-if="errors.mobile_no" class="sr-err">{{ errors.mobile_no }}</div>
        </div>
        <div class="sr-field">
          <label>Phone</label>
          <input v-model="f.phone" />
        </div>

        <div class="sr-section">Address</div>
        <div class="sr-field sr-full">
          <label>Address Line 1 <span class="req">*</span></label>
          <input v-model="f.address_line1" />
          <div v-if="errors.address_line1" class="sr-err">{{ errors.address_line1 }}</div>
        </div>
        <div class="sr-field sr-full">
          <label>Address Line 2</label>
          <input v-model="f.address_line2" />
        </div>
        <div class="sr-field">
          <label>City <span class="req">*</span></label>
          <input v-model="f.city" />
          <div v-if="errors.city" class="sr-err">{{ errors.city }}</div>
        </div>
        <div class="sr-field">
          <label>Emirate</label>
          <select v-model="f.emirate"><option v-for="e in emirates" :key="e" :value="e">{{ e }}</option></select>
        </div>
        <div class="sr-field">
          <label>Country</label>
          <input v-model="f.country" readonly />
        </div>

        <div class="sr-section">Bank (AED)</div>
        <div class="sr-field">
          <label>Bank Name</label>
          <input v-model="f.bank_name" />
        </div>
        <div class="sr-field">
          <label>Account Name</label>
          <input v-model="f.account_name" />
        </div>
        <div class="sr-field sr-full">
          <label>IBAN</label>
          <input v-model="f.iban" class="mono" placeholder="AE…" />
        </div>

        <div class="sr-section">Compliance Documents</div>
        <div class="sr-field">
          <label>Trade License <span class="req">*</span></label>
          <input type="file" accept=".pdf,.png,.jpg,.jpeg" @change="onFile('trade_license_attachment', $event)" />
          <div v-if="files.trade_license_attachment" class="sip-sub" style="margin-top:4px">{{ files.trade_license_attachment.name }}</div>
          <div v-if="errors.trade_license_attachment" class="sr-err">{{ errors.trade_license_attachment }}</div>
        </div>
        <div class="sr-field">
          <label>Trade License Validity <span class="req">*</span></label>
          <input v-model="f.trade_license_valid_until" type="date" />
          <div v-if="errors.trade_license_valid_until" class="sr-err">{{ errors.trade_license_valid_until }}</div>
        </div>
        <div class="sr-field sr-full">
          <label>Tax Registration Certificate <span class="req">*</span></label>
          <input type="file" accept=".pdf,.png,.jpg,.jpeg" @change="onFile('tax_registration_certificate', $event)" />
          <div v-if="files.tax_registration_certificate" class="sip-sub" style="margin-top:4px">{{ files.tax_registration_certificate.name }}</div>
          <div v-if="errors.tax_registration_certificate" class="sr-err">{{ errors.tax_registration_certificate }}</div>
        </div>
        <div class="sr-field">
          <label>ICV Certificate <span class="req">*</span></label>
          <input type="file" accept=".pdf,.png,.jpg,.jpeg" @change="onFile('icv_certificate', $event)" />
          <div v-if="files.icv_certificate" class="sip-sub" style="margin-top:4px">{{ files.icv_certificate.name }}</div>
          <div v-if="errors.icv_certificate" class="sr-err">{{ errors.icv_certificate }}</div>
        </div>
        <div class="sr-field">
          <label>ICV Certificate Validity <span class="req">*</span></label>
          <input v-model="f.icv_valid_until" type="date" />
          <div v-if="errors.icv_valid_until" class="sr-err">{{ errors.icv_valid_until }}</div>
        </div>
        <div class="sr-field sr-full">
          <label>IBAN Letter <span class="req">*</span></label>
          <input type="file" accept=".pdf,.png,.jpg,.jpeg" @change="onFile('iban_letter', $event)" />
          <div v-if="files.iban_letter" class="sip-sub" style="margin-top:4px">{{ files.iban_letter.name }}</div>
          <div v-if="errors.iban_letter" class="sr-err">{{ errors.iban_letter }}</div>
        </div>
        <div class="sr-field sr-full">
          <label>Additional Documents</label>
          <input type="file" accept=".pdf,.png,.jpg,.jpeg" @change="onFile('additional_documents', $event)" />
          <div v-if="files.additional_documents" class="sip-sub" style="margin-top:4px">{{ files.additional_documents.name }}</div>
        </div>

        <div class="sr-section">Other</div>
        <div class="sr-field sr-full">
          <label>Goods / Services Supplied</label>
          <textarea v-model="f.goods_services" rows="2"></textarea>
        </div>
        <div class="sr-field sr-full">
          <label>Remarks</label>
          <textarea v-model="f.remarks" rows="2"></textarea>
        </div>
      </div>

      <div v-if="formError" class="sr-err" style="margin-top:14px">{{ formError }}</div>
      <div class="sr-actions">
        <button type="button" class="sip-btn" :disabled="submitting" @click="submit">
          {{ submitting ? 'Submitting…' : 'Submit for approval' }}
        </button>
      </div>
    </section>

    <section v-else class="sr-card sr-success">
      <div class="sr-success-icon">✓</div>
      <h2 style="margin:0 0 8px">Registration submitted</h2>
      <p class="sip-sub">Reference <strong class="mono">{{ refName }}</strong> is with NumeroUNO for approval.</p>
      <p class="sip-sub">After approval, NumeroUNO AP will create your portal login so you can sign in at the Supplier Invoice Portal.</p>
      <div style="display:flex;gap:10px;justify-content:center;margin-top:18px;flex-wrap:wrap">
        <button type="button" class="sip-btn secondary" @click="reset">Register another</button>
        <a class="sip-btn" href="/supplier-invoice-portal" style="text-decoration:none;display:inline-flex;align-items:center">Invoice Portal</a>
      </div>
    </section>
  </div>
</div>
`,
	}).mount("#supplier-registration");
})();
