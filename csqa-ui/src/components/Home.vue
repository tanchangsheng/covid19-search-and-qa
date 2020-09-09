<template>
  <div class="main-body">
    <b-container fluid style="max-width:800px">
      <h1>
        <router-link :to="{ path: '/'}" style="color:#404040">Covid-19 Phase 2 Advisories Search</router-link>
      </h1>
      <!-- search bar component -->
      <b-row id="search-bar">
        <b-col cols="9" id="search-input">
          <b-form @submit="onSubmit">
            <b-input-group>
              <b-form-input v-model="text" placeholder="Search or Ask a Question"></b-form-input>
              <b-input-group-append>
                <b-button type="submit" id="search-button" variant="outline-primary">
                  <b-icon-search></b-icon-search>
                </b-button>
              </b-input-group-append>
            </b-input-group>
          </b-form>
        </b-col>
        <b-col cols="3" id="filter-button">
          <b-button style="float:right" v-b-toggle.sidebar-backdrop>Sectors</b-button>
        </b-col>
      </b-row>
      <b-sidebar id="sidebar-backdrop" title="Sectors" right backdrop shadow>
        <div class="filters">
          <b-form-group class="m-2">
            <b-form-checkbox-group
              v-model="selected"
              :options="options"
              name="sectors"
              switches
              stacked
            ></b-form-checkbox-group>
          </b-form-group>
        </div>
      </b-sidebar>

      <!-- sample questions component -->
      <div v-if="results == null || results.length == 0" id="sample-questions">
        <b>Sample questions you may ask</b>
        <ul>
          <li>
            <router-link
              :to="{ path: '/', query: { query: 'What can i do in phase 2', filters: this.filters }}"
            >What can i do in phase 2</router-link>
          </li>
          <li>
            <router-link
              :to="{ path: '/', query: { query: 'Advisory for Inbound Travellers', filters: this.filters }}"
            >Advisory for Inbound Travellers</router-link>
          </li>
          <li>
            <router-link
              :to="{ path: '/', query: { query: 'when can the cinemas open', filters: this.filters }}"
            >When can the cinemas open</router-link>
          </li>
          <li>
            <router-link
              :to="{ path: '/', query: { query: 'maximum people allowed for solemnizations', filters: this.filters }}"
            >Maximum people allowed for solemnizations</router-link>
          </li>
          <li>
            <router-link
              :to="{ path: '/', query: { query: 'maximum audience size for performances', filters: this.filters }}"
            >Maximum audience size for performances</router-link>
          </li>
        </ul>
      </div>

      <!-- answer component -->
      <div v-if="fetchingAnswers">
        <b-row>
          <b-card class="text-justify" id="result-card">
            <b-card-text id="answer-answer">Looking for answers...</b-card-text>
          </b-card>
        </b-row>
      </div>
      <div v-if="answer">
        <b-row>
          <b-card class="text-justify" id="answer-card">
            <b-card-body id="answer-card-body">
              <b-card-text id="answer-answer">{{answer.answer}}</b-card-text>
              <b-card-text v-html="answer.context" id="result-text"></b-card-text>

              <b-card-title>
                <a :href="answer.link" id="answer-title">{{answer.title}}</a>
              </b-card-title>
              <b-card-sub-title>
                <div id="result-link">{{answer.link}}</div>
              </b-card-sub-title>
            </b-card-body>
          </b-card>
        </b-row>
      </div>

      <!-- results component -->
      <div v-for="result in results" :key="result.link" id="result-li-item">
        <b-row>
          <b-card class="text-justify" id="result-card">
            <b-card-title>
              <a :href="result.link" id="result-title">{{result.title}}</a>
            </b-card-title>
            <b-card-sub-title>
              <div id="result-link">{{result.link}}</div>
            </b-card-sub-title>

            <b-card-text v-html="result.highlight" id="result-text"></b-card-text>
            <b-card-text id="result-meta">{{result.given_date}} - {{result.sector}}</b-card-text>
          </b-card>
        </b-row>
      </div>
      <!-- pagination component -->
      <div v-if="results.length > 0">
        <div class="overflow-auto">
          <b-pagination
            v-model="currentPage"
            :total-rows="total"
            :per-page="size"
            aria-controls="results-group"
            align="center"
            @input="handlePaginationInput"
          ></b-pagination>
        </div>
      </div>
    </b-container>
  </div>
</template>

<script>
import axios from "axios";

export default {
  name: "Home",
  beforeMount() {
    if (this.text != null) {
      this.answerRequest();
      this.searchRequest();
    }
  },
  methods: {
    // perform search
    searchRequest() {
      this.answer = null;
      axios
        .get("http://localhost:5000/search", {
          params: this.searchParams,
        })
        .then((response) => {
          this.results = response.data.results;
          this.total = response.data.total;
        })
        .catch((error) => {
          if (error.response) {
            console.log(error.response.data);
            console.log(error.response.status);
            console.log(error.response.headers);
          } else if (error.request) {
            console.log(error.request);
          } else {
            console.log("Error", error.message);
          }
          console.log(error.config);
        });
    },
    // perform question answering
    answerRequest() {
      this.fetchingAnswers = true;
      axios
        .get("http://localhost:5000/answers", {
          params: this.answerParams,
        })
        .then((response) => {
          this.fetchingAnswers = false;
          const data = response.data;
          this.answers = data;
          if (data != null && data.length > 0) {
            this.answer = data[0];
          } else {
            this.answer = null;
          }
        })
        .catch((error) => {
          this.fetchingAnswers = false;
          this.answer = null;
          if (error.response) {
            // The request was made and the server responded with a status code
            // that falls out of the range of 2xx
            console.log(error.response.data);
            console.log(error.response.status);
            console.log(error.response.headers);
          } else if (error.request) {
            // The request was made but no response was received
            // `error.request` is an instance of XMLHttpRequest in the browser and an instance of
            // http.ClientRequest in node.js
            console.log(error.request);
          } else {
            // Something happened in setting up the request that triggered an Error
            console.log("Error", error.message);
          }
          console.log(error.config);
        });
    },
    onSubmit(event) {
      event.preventDefault();
      if (this.filters != null && this.filters.length > 0) {
        this.$router.push({
          path: "/",
          query: { query: this.text, filters: this.filters },
        });
      } else {
        this.$router.push({ path: "/", query: { query: this.text } });
      }
    },
    handlePaginationInput(page) {
      this.start = (page - 1) * 10;
      this.searchRequest();
    },
  },
  computed: {
    filters() {
      if (this.selected != null) {
        return this.selected.join("|");
      }
      return null;
    },
    searchParams() {
      const params = new URLSearchParams();
      params.append("query", this.text);
      if (this.filters != null && this.filters.length > 0) {
        params.append("filters", this.filters);
      } else if (this.filtersParam != null && this.filtersParam.length > 0) {
        params.append("filters", this.filtersParam);
      }
      params.append("start", this.start);
      params.append("size", this.size);
      return params;
    },
    answerParams() {
      const params = new URLSearchParams();
      params.append("query", this.text);
      if (this.filters != null && this.filters.length > 0) {
        params.append("filters", this.filters);
      } else if (this.filtersParam != null && this.filtersParam.length > 0) {
        params.append("filters", this.filtersParam);
      }
      return params;
    },
  },
  data() {
    return {
      text: this.$route.query.query,
      filtersParam: this.$route.query.filters,
      start: 0,
      size: 10,
      results: [],
      total: 0,
      currentPage: 1,
      answer: null,
      answers: [],
      selected:
        this.$route.query.filters == null
          ? []
          : this.$route.query.filters.split("|"),
      fetchingAnswers: false,
      options: [
        "Building and Construction Authority (BCA)",
        "Council for Estate Agencies (CEA)",
        "Enterprise Singapore (ESG)",
        "GoBusiness COVID",
        "Infocomm Media Development Authority (IMDA)",
        "Maritime and Port Authority (MPA)",
        "Ministry of Culture, Community and Youth (MCCY)",
        "Ministry of Education (MOE)",
        "Ministry of Health (MOH)",
        "Ministry of Manpower (MOM)",
        "Ministry of Social and Family Development (MSF)",
        "Monetary Authority of Singapore (MAS)",
        "National Arts Council (NAC)",
        "National Environment Agency (NEA)",
        "National Heritage Board (NHB)",
        "National Parks (Nparks)",
        "Singapore Land Authority (SLA)",
        "Singapore Police Force (SPF)",
        "Singapore Tourism Board (STB)",
        "Sport Singapore (SportSG)",
        "Urban Redevelopment Authority (URA)",
      ],
    };
  },
};
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
#search-bar {
  margin: 0.5rem;
}
#search-input {
  margin: 0;
  padding: 0;
}
#filter-button {
  margin-left: 0;
  padding: 0;
}
#sample-questions {
  text-align: left;
  margin: 1rem;
}
.card {
  /* border: none; */
}
.card-body {
  padding-bottom: 0.5rem;
  padding-top: 0.5rem;
}
.card-title {
  margin-bottom: 0.5rem;
}
#answer-card {
  margin-left: 1.5rem;
  margin-right: 1.5rem;
  margin-top: 0.5rem;
}
#answer-card-body {
  padding: 0.5rem;
}
#answer-answer {
  font-size: 1.5rem;
  margin-bottom: 0;
}
#answer-title {
  font-size: 1.25rem;
  color: #4d79ff;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 1; /* number of lines to show */
  -webkit-box-orient: vertical;
}
#result-card {
  border: none;
  margin: 0.5rem;
}
#result-title {
  color: #4d79ff;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2; /* number of lines to show */
  -webkit-box-orient: vertical;
}
#result-text {
  /* text-align: left; */
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 4; /* number of lines to show */
  -webkit-box-orient: vertical;
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}
#result-link {
  color: grey;
  text-align: left;
  font-size: small;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 1; /* number of lines to show */
  -webkit-box-orient: vertical;
}
#result-meta {
  font-size: small;
  color: #809fff;
}
.filters {
  text-align: left;
}
</style>
