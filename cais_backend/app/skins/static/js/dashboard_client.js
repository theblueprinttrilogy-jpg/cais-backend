/**
 * CAIS Dashboard API Client
 * Version: 10.0
 *
 * Secure, production-ready client for the CAIS Code Compliance backend.
 * Provides robust fetch wrappers with JWT authentication, error handling,
 * and response validation.
 *
 * All methods return Promises and throw descriptive errors on failure.
 * No mock data is used; all requests connect directly to the backend.
 */

(function (global) {
    'use strict';

    // ============================================================
    // Configuration
    // ============================================================

    const DEFAULT_BASE_URL = '/api/v1';
    const DEFAULT_FORENSIC_URL = '/forensic';

    // ============================================================
    // Utility Functions
    // ============================================================

    /**
     * Safely retrieve the JWT token from storage.
     * @returns {string|null} The token or null if not found.
     */
    function getToken() {
        try {
            return localStorage.getItem('cais_jwt_token');
        } catch (e) {
            return null;
        }
    }

    /**
     * Set the JWT token in storage.
     * @param {string} token
     */
    function setToken(token) {
        try {
            localStorage.setItem('cais_jwt_token', token);
        } catch (e) {
            // Ignore storage errors
        }
    }

    /**
     * Remove the JWT token from storage.
     */
    function clearToken() {
        try {
            localStorage.removeItem('cais_jwt_token');
        } catch (e) {
            // Ignore storage errors
        }
    }

    /**
     * Build headers for a request, including Authorization if token exists.
     * @param {Object} customHeaders - Additional headers to merge.
     * @param {boolean} isFormData - Whether the body is FormData (prevents Content-Type).
     * @returns {Headers} Headers object.
     */
    function buildHeaders(customHeaders = {}, isFormData = false) {
        const headers = new Headers();
        const token = getToken();
        if (token) {
            headers.set('Authorization', `Bearer ${token}`);
        }
        // If not FormData, set Content-Type to JSON
        if (!isFormData) {
            headers.set('Content-Type', 'application/json');
        }
        // Merge custom headers
        for (const [key, value] of Object.entries(customHeaders)) {
            headers.set(key, value);
        }
        return headers;
    }

    /**
     * Validate that a response is OK and has valid JSON structure.
     * @param {Response} response - The fetch response.
     * @param {string} context - A descriptive context for error messages.
     * @returns {Promise<Object>} Parsed JSON.
     * @throws {Error} If response status is not OK or body is malformed.
     */
    async function validateResponse(response, context) {
        let data;
        try {
            data = await response.json();
        } catch (e) {
            throw new Error(`Invalid JSON response from ${context}: ${e.message}`);
        }

        if (!response.ok) {
            const detail = data.detail || data.message || `HTTP ${response.status}`;
            throw new Error(`API error (${context}): ${detail}`);
        }

        // Optional: validate that data is an object
        if (typeof data !== 'object' || data === null) {
            throw new Error(`Response from ${context} is not a valid object.`);
        }

        return data;
    }

    /**
     * Perform a fetch with automatic JSON serialization/deserialization,
     * header management, and error handling.
     * @param {string} url - Full URL or relative path.
     * @param {Object} options - Fetch options (method, body, headers, etc.).
     * @param {string} context - Context for error messages.
     * @returns {Promise<Object>} Parsed JSON response.
     */
    async function request(url, options = {}, context = 'request') {
        const method = options.method || 'GET';
        const isFormData = options.body instanceof FormData;

        const headers = buildHeaders(options.headers || {}, isFormData);

        const fetchOptions = {
            method,
            headers,
            credentials: 'include', // For cookies if needed
        };

        // Only add body if not GET/HEAD
        if (method !== 'GET' && method !== 'HEAD' && options.body !== undefined) {
            fetchOptions.body = isFormData ? options.body : JSON.stringify(options.body);
        }

        let fullUrl = url;
        // If url is relative, prepend base URL
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            // Use the appropriate base
            const base = url.startsWith('/forensic') ? DEFAULT_FORENSIC_URL : DEFAULT_BASE_URL;
            fullUrl = base + url;
        }

        try {
            const response = await fetch(fullUrl, fetchOptions);
            return await validateResponse(response, context);
        } catch (error) {
            if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
                throw new Error(`Network error (${context}): Unable to reach the server.`);
            }
            throw error;
        }
    }

    // ============================================================
    // Main API Client Class
    // ============================================================

    /**
     * CAIS Dashboard API Client.
     * Provides methods for all backend interactions.
     */
    class CaisApiClient {
        /**
         * Set or update the authentication token.
         * @param {string} token - JWT token.
         */
        static setAuthToken(token) {
            setToken(token);
        }

        /**
         * Clear the authentication token.
         */
        static clearAuthToken() {
            clearToken();
        }

        /**
         * Get the current token (for debugging).
         * @returns {string|null}
         */
        static getAuthToken() {
            return getToken();
        }

        // ============================================================
        // Core Endpoints (from app.api.endpoints)
        // ============================================================

        /**
         * Perform semantic search for code references.
         * @param {string} query - Natural language query.
         * @param {number} limit - Max results (default 10).
         * @returns {Promise<Object>} SearchResponse.
         */
        static async search(query, limit = 10) {
            const body = { query, limit };
            return request('/search', {
                method: 'POST',
                body,
            }, 'semantic_search');
        }

        /**
         * Perform a deterministic compliance audit.
         * @param {string} jurisdiction - e.g., 'US-FL'
         * @param {string} codeType - e.g., 'building'
         * @param {string[]} compliantSections - List of sections claimed compliant.
         * @returns {Promise<Object>} AuditResponse.
         */
        static async audit(jurisdiction, codeType, compliantSections = []) {
            const body = { jurisdiction, code_type: codeType, compliant_sections: compliantSections };
            return request('/audit', {
                method: 'POST',
                body,
            }, 'compliance_audit');
        }

        /**
         * Upload a construction document for processing.
         * @param {File} file - The PDF file.
         * @returns {Promise<Object>} UploadResponse (task_id, status).
         */
        static async uploadDocument(file) {
            const formData = new FormData();
            formData.append('file', file);
            return request('/upload', {
                method: 'POST',
                body: formData,
            }, 'document_upload');
        }

        // ============================================================
        // Forensic Compliance Router (app.routers.forensic_compliance)
        // ============================================================

        /**
         * Perform a full forensic audit on a construction plan file.
         * @param {File} file - The file (PDF, DWG, RVT, IFC, DXF, PNG, JPG, JPEG).
         * @param {string} jurisdiction - Default 'US-FL'.
         * @param {string} codeType - Default 'building'.
         * @returns {Promise<Object>} Forensic audit response.
         */
        static async forensicAuditPlan(file, jurisdiction = 'US-FL', codeType = 'building') {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('jurisdiction', jurisdiction);
            formData.append('code_type', codeType);
            return request('/forensic/audit-plan', {
                method: 'POST',
                body: formData,
            }, 'forensic_audit');
        }

        // ============================================================
        // Dashboard-Specific Methods
        // ============================================================

        /**
         * Fetch a list of recent forensic audit reports.
         * @param {number} limit - Number of reports (default 20).
         * @returns {Promise<Object>} { reports: Array }
         */
        static async getForensicReports(limit = 20) {
            // This endpoint is not defined in the given code, but we'll assume
            // the backend provides it. We'll construct a query.
            return request('/forensic/reports?limit=' + limit, {
                method: 'GET',
            }, 'get_forensic_reports');
        }

        /**
         * Fetch the status of a specific inspection/task.
         * @param {string} taskId - The task ID returned from upload.
         * @returns {Promise<Object>} { status, result, etc. }
         */
        static async getInspectionStatus(taskId) {
            return request(`/tasks/${taskId}/status`, {
                method: 'GET',
            }, 'get_inspection_status');
        }

        /**
         * Fetch an evidence image by its path or ID.
         * @param {string} imagePath - The image URL or path.
         * @returns {Promise<Blob>} The image blob.
         */
        static async getEvidenceImage(imagePath) {
            // If it's a full URL, use it; otherwise, build from base.
            let url = imagePath;
            if (!url.startsWith('http://') && !url.startsWith('https://')) {
                // Assume it's a relative path under the forensic endpoint
                url = '/forensic/evidence/' + imagePath.replace(/^\/+/, '');
            }
            const headers = buildHeaders({});
            const response = await fetch(url, {
                method: 'GET',
                headers,
                credentials: 'include',
            });
            if (!response.ok) {
                const text = await response.text().catch(() => '');
                throw new Error(`Failed to fetch evidence image: ${response.status} ${text}`);
            }
            const blob = await response.blob();
            if (!blob.type.startsWith('image/')) {
                throw new Error(`Retrieved content is not an image.`);
            }
            return blob;
        }

        // ============================================================
        // Additional Utilities
        // ============================================================

        /**
         * Health check.
         * @returns {Promise<Object>} { status: 'healthy' }
         */
        static async healthCheck() {
            return request('/health', {
                method: 'GET',
            }, 'health_check');
        }
    }

    // ============================================================
    // Expose to global scope for browser
    // ============================================================

    global.CaisApiClient = CaisApiClient;

    // Also export as module if using module systems
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = CaisApiClient;
    }

})(typeof window !== 'undefined' ? window : global);
